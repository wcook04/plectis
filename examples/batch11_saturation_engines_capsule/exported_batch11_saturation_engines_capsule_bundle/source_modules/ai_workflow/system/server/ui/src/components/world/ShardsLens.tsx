// [PURPOSE] The queryable shard lens mounted at /station/shards. Three panes —
// ranked query, interactive relationship graph, and shard-detail with authority
// chain — projected over the read-only shard world-model endpoints Codex
// landed (/api/world-model/shards/{overview,query,{shard_id}}).
//
// The lens preserves the shard substrate's first-class fields (voice_anchor,
// clarified_statement, gestures_towards, idea_group_ids, parent_paragraph_id,
// routing_targets, provenance) as distinct UI elements instead of flattening
// them into prose.
//
// Doctrine:
//   - mech_025 (authority chain contract) — drill-down on shard, paragraph,
//     group, doctrine targets.
//   - pri_057 / pri_059 / pri_069 — ontology-first navigation, authorities
//     projected by the surface.
//   - pri_104 / pri_109 — frontend observability + fail-loud state guards.
//   - Prime Directive (CLAUDE.md) — preserve Will's voice anchors verbatim
//     instead of paraphrasing. The detail pane presents voice_anchor as a
//     pull-quote next to the clarified_statement, never in place of it.
import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type KeyboardEvent,
  type ReactNode,
} from 'react';
import { useLocation, useNavigate, useSearchParams } from 'react-router-dom';
import clsx from 'clsx';
import {
  ArrowUpRight,
  FileCode2,
  Filter,
  Hash,
  Quote,
  RefreshCw,
  Search,
  Target,
  Waypoints,
  X,
} from 'lucide-react';

import {
  api,
  apiErrorKind,
  type ShardGraphNode,
  type ShardGraphPayload,
  type ShardLensDetailResponse,
  type ShardLensOverviewResponse,
  type ShardLensQueryResponse,
  type ShardQueryResult,
  type ShardRelatedResult,
  type ShardSource,
} from '../../api';
import AuthorityChip, { type AuthorityKind } from './AuthorityChip';
import AuthorityChainView from './AuthorityChainView';
import { PanelHead } from './cellHelpers';
import DoctrineDrillDown, { type DoctrineDrillDownKind } from './DoctrineDrillDown';
import FreshnessBadge from './FreshnessBadge';
import LifecycleChip from './LifecycleChip';
import MapScroll from './MapScroll';
import { buildMapScrollLayout, type MapScrollLayout } from './mapScrollLayout';
import StateGuard from './StateGuard';
import ShardGraph, { ShardGraphLegend } from './ShardGraph';
import { useCaptureBudgetBlocker, useCaptureDiagnostic } from '../../lib/captureMode';
import { readRecentSurfaces, rememberRecentSurface } from '../../navigation/recentSurfaces';
import { buildInspectorFileRoute } from '../../navigation/inspectorRoutes';
import { withReturnToQuery } from '../../navigation/turnaround';
import { useZenith } from '../../stores/useZenith';
import { buildPaletteSections } from '../CommandPalette.utils';

const SHARD_SOURCES: ShardSource[] = ['family', 'active', 'raw_seed'];

interface AsyncResource<T> {
  key: string;
  data: T | null;
  error: Error | string | null;
}

function asString(value: unknown): string {
  return typeof value === 'string' ? value : '';
}

function asStringArray(value: unknown): string[] {
  return Array.isArray(value)
    ? value.filter((item): item is string => typeof item === 'string')
    : [];
}

function asRecordArray(value: unknown): Array<Record<string, unknown>> {
  return Array.isArray(value)
    ? value.filter((item): item is Record<string, unknown> => !!item && typeof item === 'object')
    : [];
}

function isAbortError(error: unknown): boolean {
  return (
    (typeof DOMException !== 'undefined' && error instanceof DOMException && error.name === 'AbortError')
    || (!!error && typeof error === 'object' && 'name' in error && (error as { name?: string }).name === 'AbortError')
  );
}

function shardLabel(shard: Record<string, unknown>): string {
  const statement = asString(shard.clarified_statement);
  if (statement) return statement;
  const voice = asString(shard.voice_anchor);
  if (voice) return voice;
  return asString(shard.id) || 'Untitled shard';
}

function shardStatus(shard: Record<string, unknown>): {
  routing?: string;
  coverage?: string;
  status?: string;
} {
  return {
    routing: asString(shard.routing_state) || undefined,
    coverage: asString(shard.coverage_state) || undefined,
    status: asString(shard.status) || undefined,
  };
}

function extractRoutingTargets(
  shard: Record<string, unknown>,
): Array<{ target_id: string; kind: string; title?: string }> {
  return asRecordArray(shard.routing_targets)
    .map((entry) => {
      const target = asString(entry.target_id) || asString(entry.id);
      const kind = asString(entry.kind) || asString(entry.target_kind) || 'concept';
      const title = asString(entry.title) || undefined;
      return target ? { target_id: target, kind, ...(title ? { title } : {}) } : null;
    })
    .filter((entry): entry is { target_id: string; kind: string; title?: string } => !!entry);
}

function doctrineKind(kind: string): AuthorityKind {
  if (kind === 'mechanism') return 'mechanism';
  if (kind === 'principle') return 'principle';
  if (kind === 'standard') return 'standard';
  if (kind === 'contract') return 'contract';
  return 'concept';
}

function fileLabel(path: string): string {
  const parts = path.split('/').filter(Boolean);
  if (parts.length <= 2) return path;
  return `…/${parts.slice(-2).join('/')}`;
}

function shardGraphFilePath(node: ShardGraphNode): string | null {
  if (node.kind !== 'file') return null;
  const candidate = node.source_path ?? node.id;
  return typeof candidate === 'string' && candidate.trim().length > 0 ? candidate : null;
}

function tonefulBadge({
  tone,
  children,
  className,
}: {
  tone: 'ok' | 'warn' | 'muted' | 'accent';
  children: ReactNode;
  className?: string;
}) {
  return (
    <span
      className={clsx(
        'inline-flex items-center gap-1 rounded-full border px-2 py-0.5 font-mono text-[9px] uppercase tracking-[0.18em]',
        tone === 'ok' && 'border-emerald-400/30 bg-emerald-500/10 text-emerald-200',
        tone === 'warn' && 'border-amber-400/30 bg-amber-500/10 text-amber-200',
        tone === 'muted' && 'border-zenith-edge bg-white/[0.04] text-white/60',
        tone === 'accent' &&
          'border-[var(--zenith-accent-edge)] bg-[var(--zenith-accent-soft)] text-[var(--zenith-accent)]',
        className,
      )}
    >
      {children}
    </span>
  );
}

// Minimal, purposeful mapping from routing/coverage states to tones. We keep
// the raw state string visible so the operator still sees the exact substrate
// vocabulary — tone is decoration, not a rewrite.
function stateTone(value?: string): 'ok' | 'warn' | 'muted' | 'accent' {
  if (!value) return 'muted';
  if (/fresh|routed|addressed|linked|complete/.test(value)) return 'ok';
  if (/needs|pending|review/.test(value)) return 'warn';
  if (/drift|broken|stale/.test(value)) return 'warn';
  return 'muted';
}

function MatchedAxesBar({
  axes,
  maxScore,
}: {
  axes: ShardQueryResult['matched_axes'];
  maxScore: number;
}) {
  if (axes.length === 0) return null;
  return (
    <div className="mt-1 flex flex-wrap gap-1">
      {axes.map((axis, index) => {
        const width = maxScore > 0 ? Math.max(6, Math.round((axis.score / maxScore) * 100)) : 30;
        return (
          <span
            key={`axis:${axis.axis}:${axis.score}:${index}`}
            className="inline-flex items-center gap-1 overflow-hidden rounded-full border border-zenith-edge bg-white/[0.03] px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-[0.16em] text-zenith-soft"
            title={axis.matched_terms.join(', ')}
          >
            <span className="inline-block h-[3px] w-8 overflow-hidden rounded-full bg-white/10">
              <span
                aria-hidden
                className="block h-full rounded-full bg-[var(--zenith-accent)]"
                style={{ width: `${width}%` }}
              />
            </span>
            <span>{axis.axis}</span>
            <span className="text-zenith-muted">{axis.score}</span>
          </span>
        );
      })}
    </div>
  );
}

interface DrillTarget {
  kind: DoctrineDrillDownKind;
  target: string;
}

type ShardBrowseSectionKind = 'group' | 'paragraph' | 'routing' | 'standalone';

type ShardBrowseSectionAction =
  | { kind: 'group'; label: string; value: string }
  | { kind: 'paragraph'; label: string; value: string }
  | { kind: 'drill'; label: string; target: DrillTarget }
  | null;

interface ShardBrowseSection {
  key: string;
  kind: ShardBrowseSectionKind;
  kicker: string;
  label: string;
  action: ShardBrowseSectionAction;
  results: ShardQueryResult[];
}

function shardGroupIds(shard: Record<string, unknown>): string[] {
  const groups = asStringArray(shard.idea_group_ids);
  const primary = asString(shard.group);
  if (primary && !groups.includes(primary)) {
    groups.unshift(primary);
  }
  return groups.filter(Boolean);
}

function browsePriority(context: { group: string; paragraphId: string }): ShardBrowseSectionKind[] {
  if (context.group && context.paragraphId) {
    return ['routing', 'standalone', 'group', 'paragraph'];
  }
  if (context.group) {
    return ['paragraph', 'routing', 'standalone', 'group'];
  }
  if (context.paragraphId) {
    return ['group', 'routing', 'standalone', 'paragraph'];
  }
  return ['group', 'paragraph', 'routing', 'standalone'];
}

function browseSectionForResult(
  result: ShardQueryResult,
  context: { group: string; paragraphId: string },
): Omit<ShardBrowseSection, 'results'> {
  const shard = result.shard;
  const groups = shardGroupIds(shard);
  const paragraph = asString(shard.parent_paragraph_id) || asStringArray(shard.raw_paragraph_ids)[0];
  const route = extractRoutingTargets(shard)[0];

  for (const kind of browsePriority(context)) {
    if (kind === 'group' && groups[0]) {
      return {
        key: `group:${groups[0]}`,
        kind,
        kicker: 'idea group',
        label: groups[0],
        action: { kind: 'group', label: 'filter group', value: groups[0] },
      };
    }
    if (kind === 'paragraph' && paragraph) {
      return {
        key: `paragraph:${paragraph}`,
        kind,
        kicker: 'same paragraph',
        label: paragraph,
        action: { kind: 'paragraph', label: 'filter paragraph', value: paragraph },
      };
    }
    if (kind === 'routing' && route) {
      const targetKind: DoctrineDrillDownKind =
        route.kind === 'mechanism'
          ? 'mechanism'
          : route.kind === 'principle'
            ? 'principle'
            : 'concept';
      return {
        key: `routing:${route.kind}:${route.target_id}`,
        kind,
        kicker: `routes to ${route.kind}`,
        label: route.title ?? route.target_id,
        action: {
          kind: 'drill',
          label: `open ${route.kind}`,
          target: { kind: targetKind, target: route.target_id },
        },
      };
    }
  }

  return {
    key: `standalone:${result.shard_id}`,
    kind: 'standalone',
    kicker: 'single shard',
    label: result.shard_id,
    action: null,
  };
}

function groupShardResults(
  results: ShardQueryResult[],
  context: { group?: string; paragraphId?: string } = {},
): ShardBrowseSection[] {
  const sections: ShardBrowseSection[] = [];
  const byKey = new Map<string, ShardBrowseSection>();
  const normalizedContext = {
    group: context.group ?? '',
    paragraphId: context.paragraphId ?? '',
  };

  for (const result of results) {
    const seed = browseSectionForResult(result, normalizedContext);
    const existing = byKey.get(seed.key);
    if (existing) {
      existing.results.push(result);
      continue;
    }
    const next: ShardBrowseSection = {
      ...seed,
      results: [result],
    };
    byKey.set(seed.key, next);
    sections.push(next);
  }
  return sections;
}

export default function ShardsLens() {
  const navigationGraph = useZenith((state) => state.worldModel?.navigation_graph ?? null);
  const location = useLocation();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();

  const source = (searchParams.get('source') as ShardSource | null) ?? 'family';
  const query = searchParams.get('q') ?? '';
  const group = searchParams.get('group') ?? '';
  const paragraphId = searchParams.get('paragraph') ?? '';
  const status = searchParams.get('status') ?? '';
  const selectedShardId = searchParams.get('shard') ?? '';

  const filterKey = `${query}\u0000${group}\u0000${paragraphId}\u0000${status}`;
  const [draftFilters, setDraftFilters] = useState(() => ({
    key: filterKey,
    query,
    group,
    paragraphId,
    status,
  }));
  const activeDraftFilters =
    draftFilters.key === filterKey
      ? draftFilters
      : {
          key: filterKey,
          query,
          group,
          paragraphId,
          status,
        };
  const [refreshNonce, setRefreshNonce] = useState(0);

  const overviewRequestKey = `overview:${source}:${refreshNonce}`;
  const resultsRequestKey = `${source}\u0000${query}\u0000${group}\u0000${paragraphId}\u0000${status}\u0000${refreshNonce}`;
  const detailRequestKey = selectedShardId
    ? `${source}\u0000${selectedShardId}\u0000${refreshNonce}`
    : '';
  const [overviewResource, setOverviewResource] = useState<AsyncResource<ShardLensOverviewResponse>>({
    key: '',
    data: null,
    error: null,
  });
  const [resultsResource, setResultsResource] = useState<AsyncResource<ShardLensQueryResponse>>({
    key: '',
    data: null,
    error: null,
  });
  const [detailResource, setDetailResource] = useState<AsyncResource<ShardLensDetailResponse>>({
    key: '',
    data: null,
    error: null,
  });
  const overview = overviewResource.data;
  const overviewLoading = overviewResource.key !== overviewRequestKey && !overviewResource.data;
  const overviewError =
    overviewResource.key === overviewRequestKey ? overviewResource.error : null;
  const results = resultsResource.data;
  const resultsLoading = resultsResource.key !== resultsRequestKey && !resultsResource.data;
  const resultsError = resultsResource.key === resultsRequestKey ? resultsResource.error : null;
  const detail =
    selectedShardId && detailResource.key === detailRequestKey ? detailResource.data : null;
  const detailLoading = Boolean(selectedShardId && detailResource.key !== detailRequestKey);
  const detailError = detailResource.key === detailRequestKey ? detailResource.error : null;

  const [drill, setDrill] = useState<DrillTarget | null>(null);

  const resultListRef = useRef<HTMLDivElement | null>(null);
  const currentRoute = `${location.pathname}${location.search}${location.hash}`;
  const mapScroll = useMemo(
    () =>
      buildMapScrollLayout(
        buildPaletteSections('', location.pathname, location.search, {
          navigationGraph,
          recentSurfaces: readRecentSurfaces(),
        }),
      ),
    [location.pathname, location.search, navigationGraph],
  );

  const setDraftField = useCallback(
    (field: 'query' | 'group' | 'paragraphId' | 'status', value: string) => {
      setDraftFilters((current) => {
        const base =
          current.key === filterKey
            ? current
            : {
                key: filterKey,
                query,
                group,
                paragraphId,
                status,
              };
        return { ...base, [field]: value };
      });
    },
    [filterKey, group, paragraphId, query, status],
  );

  useEffect(() => {
    let alive = true;
    const controller = new AbortController();
    void api.worldModel
      .shardsOverview({ source }, { signal: controller.signal })
      .then((payload) => {
        if (alive) {
          setOverviewResource({ key: overviewRequestKey, data: payload, error: null });
        }
      })
      .catch((error: unknown) => {
        if (!alive || isAbortError(error)) return;
        setOverviewResource({
          key: overviewRequestKey,
          data: null,
          error: error instanceof Error ? error : 'Failed to load shard overview',
        });
      });
    return () => {
      alive = false;
      controller.abort();
    };
  }, [overviewRequestKey, source]);

  useEffect(() => {
    let alive = true;
    const controller = new AbortController();
    void api.worldModel
      .queryShards({
        source,
        query: query || undefined,
        group: group || undefined,
        paragraph_id: paragraphId || undefined,
        status: status || undefined,
        limit: 20,
        related_limit: 40,
      }, { signal: controller.signal })
      .then((payload) => {
        if (alive) {
          setResultsResource({ key: resultsRequestKey, data: payload, error: null });
        }
      })
      .catch((error: unknown) => {
        if (!alive || isAbortError(error)) return;
        setResultsResource({
          key: resultsRequestKey,
          data: null,
          error: error instanceof Error ? error : 'Failed to query shards',
        });
      });
    return () => {
      alive = false;
      controller.abort();
    };
  }, [group, paragraphId, query, resultsRequestKey, source, status]);

  useEffect(() => {
    if (!results || selectedShardId) return;
    const fallbackShardId = results.results[0]?.shard_id ?? '';
    if (!fallbackShardId) return;
    const next = new URLSearchParams(searchParams);
    next.set('shard', fallbackShardId);
    setSearchParams(next, { replace: true });
  }, [results, searchParams, selectedShardId, setSearchParams]);

  useEffect(() => {
    if (!selectedShardId) return;
    let alive = true;
    const controller = new AbortController();
    void api.worldModel
      .shardDetail(selectedShardId, { source, neighbors: 3 }, { signal: controller.signal })
      .then((payload) => {
        if (alive) {
          setDetailResource({ key: detailRequestKey, data: payload, error: null });
        }
      })
      .catch((error: unknown) => {
        if (!alive || isAbortError(error)) return;
        setDetailResource({
          key: detailRequestKey,
          data: null,
          error: error instanceof Error ? error : 'Failed to load shard detail',
        });
      });
    return () => {
      alive = false;
      controller.abort();
    };
  }, [detailRequestKey, selectedShardId, source]);

  const graph: ShardGraphPayload | null = useMemo(() => {
    return detail?.graph ?? results?.graph ?? null;
  }, [detail?.graph, results?.graph]);
  const selectedResult = useMemo<ShardQueryResult | ShardRelatedResult | null>(() => {
    if (!selectedShardId || !results) return null;
    return (
      results.results.find((entry) => entry.shard_id === selectedShardId) ??
      results.related.find((entry) => entry.shard_id === selectedShardId) ??
      null
    );
  }, [results, selectedShardId]);
  const graphLoading = graph == null && (resultsLoading || detailLoading);
  const graphError = resultsError ?? (graph == null ? detailError : null);

  const maxResultScore = useMemo(() => {
    if (!results) return 0;
    return results.results.reduce((acc, r) => Math.max(acc, r.score), 0);
  }, [results]);

  const applyFilters = useCallback(() => {
    const next = new URLSearchParams(searchParams);
    next.set('source', source);
    if (activeDraftFilters.query.trim()) next.set('q', activeDraftFilters.query.trim());
    else next.delete('q');
    if (activeDraftFilters.group.trim()) next.set('group', activeDraftFilters.group.trim());
    else next.delete('group');
    if (activeDraftFilters.paragraphId.trim()) next.set('paragraph', activeDraftFilters.paragraphId.trim());
    else next.delete('paragraph');
    if (activeDraftFilters.status.trim()) next.set('status', activeDraftFilters.status.trim());
    else next.delete('status');
    next.delete('shard');
    setSearchParams(next);
  }, [
    activeDraftFilters.group,
    activeDraftFilters.paragraphId,
    activeDraftFilters.query,
    activeDraftFilters.status,
    searchParams,
    setSearchParams,
    source,
  ]);

  const clearFilters = useCallback(() => {
    setDraftFilters({
      key: filterKey,
      query: '',
      group: '',
      paragraphId: '',
      status: '',
    });
    const next = new URLSearchParams(searchParams);
    next.set('source', source);
    next.delete('q');
    next.delete('group');
    next.delete('paragraph');
    next.delete('status');
    next.delete('shard');
    setSearchParams(next);
  }, [filterKey, searchParams, setSearchParams, source]);

  const selectSource = useCallback(
    (nextSource: ShardSource) => {
      const next = new URLSearchParams(searchParams);
      next.set('source', nextSource);
      next.delete('shard');
      setSearchParams(next);
    },
    [searchParams, setSearchParams],
  );

  const selectShard = useCallback(
    (shardId: string) => {
      if (!shardId) return;
      const next = new URLSearchParams(searchParams);
      next.set('shard', shardId);
      setSearchParams(next);
    },
    [searchParams, setSearchParams],
  );

  const setFilter = useCallback(
    (partial: { group?: string; paragraph?: string; status?: string; query?: string }) => {
      const next = new URLSearchParams(searchParams);
      next.set('source', source);
      if (partial.group !== undefined) {
        if (partial.group) next.set('group', partial.group);
        else next.delete('group');
      }
      if (partial.paragraph !== undefined) {
        if (partial.paragraph) next.set('paragraph', partial.paragraph);
        else next.delete('paragraph');
      }
      if (partial.status !== undefined) {
        if (partial.status) next.set('status', partial.status);
        else next.delete('status');
      }
      if (partial.query !== undefined) {
        if (partial.query) next.set('q', partial.query);
        else next.delete('q');
      }
      next.delete('shard');
      setSearchParams(next);
    },
    [searchParams, setSearchParams, source],
  );

  const openDrill = useCallback((target: DrillTarget) => {
    setDrill(target);
  }, []);

  const closeDrill = useCallback(() => setDrill(null), []);

  const openFileSurface = useCallback(
    (path: string) => {
      if (!path.trim()) return;
      const route = buildInspectorFileRoute(path, { returnTo: currentRoute });
      rememberRecentSurface(route, 'Inspector');
      navigate(route);
    },
    [currentRoute, navigate],
  );

  const openSurfaceRoute = useCallback(
    (route: string, label: string) => {
      const targetRoute = withReturnToQuery(route, currentRoute);
      rememberRecentSurface(targetRoute, label);
      navigate(targetRoute);
    },
    [currentRoute, navigate],
  );

  const handleGraphNode = useCallback(
    (node: ShardGraphNode) => {
      switch (node.kind) {
        case 'shard': {
          const shardId = node.shard_id ?? node.id;
          selectShard(shardId);
          return;
        }
        case 'paragraph': {
          openDrill({ kind: 'raw_seed_paragraph', target: node.id });
          return;
        }
        case 'group': {
          setFilter({ group: node.id, paragraph: '' });
          return;
        }
        case 'doctrine_target': {
          const [kindRaw, ...rest] = node.id.split(':');
          const targetId = rest.join(':') || kindRaw;
          const kindToken = rest.length > 0 ? kindRaw : 'concept';
          if (kindToken === 'principle' || kindToken === 'concept' || kindToken === 'mechanism') {
            openDrill({ kind: kindToken, target: targetId });
          } else {
            openDrill({ kind: 'concept', target: targetId });
          }
          return;
        }
        case 'file': {
          const path = shardGraphFilePath(node);
          if (path) {
            openFileSurface(path);
          }
          return;
        }
        default:
          return;
      }
    },
    [openDrill, openFileSurface, selectShard, setFilter],
  );

  const orderedShardIds = useMemo(
    () => (results?.results ?? []).map((r) => r.shard_id),
    [results],
  );
  const browseSections = useMemo(
    () =>
      groupShardResults(results?.results ?? [], {
        group,
        paragraphId,
      }),
    [group, paragraphId, results?.results],
  );

  const routeMismatchError = useMemo(() => {
    const errors = [overviewError, resultsError, detailError];
    return errors.find((error) => apiErrorKind(error) === 'missing_shard_routes') ?? null;
  }, [detailError, overviewError, resultsError]);
  const captureErrorMessage = useMemo(() => {
    if (routeMismatchError) {
      return routeMismatchError instanceof Error ? routeMismatchError.message : String(routeMismatchError);
    }
    const generic = detailError ?? resultsError ?? overviewError;
    if (!generic) return null;
    return generic instanceof Error ? generic.message : String(generic);
  }, [detailError, overviewError, resultsError, routeMismatchError]);
  const surfaceReady = useMemo(() => {
    if (routeMismatchError) return true;
    if (overviewLoading || resultsLoading) return false;
    if (!overview || !results) return false;
    if (!selectedShardId) return true;
    if (detailLoading) return false;
    return Boolean(detail || detailError);
  }, [
    detail,
    detailError,
    detailLoading,
    overview,
    overviewLoading,
    results,
    resultsLoading,
    routeMismatchError,
    selectedShardId,
  ]);

  const shardsDataPending =
    (overview == null && !overviewError)
    || (results == null && !resultsError)
    || (Boolean(selectedShardId) && detail == null && !detailError);
  const shardsBudgetElapsed = useCaptureBudgetBlocker(shardsDataPending, 'shards-data');
  useCaptureDiagnostic(
    routeMismatchError ? 'route_mismatch' : captureErrorMessage ? 'http_error' : null,
    captureErrorMessage,
  );

  const handleResultKey = useCallback(
    (event: KeyboardEvent<HTMLDivElement>) => {
      if (event.key !== 'ArrowDown' && event.key !== 'ArrowUp') return;
      if (orderedShardIds.length === 0) return;
      event.preventDefault();
      const currentIdx = orderedShardIds.indexOf(selectedShardId);
      const delta = event.key === 'ArrowDown' ? 1 : -1;
      const startIdx = currentIdx === -1 ? 0 : currentIdx + delta;
      const clamped = Math.max(0, Math.min(orderedShardIds.length - 1, startIdx));
      const nextShardId = orderedShardIds[clamped];
      if (nextShardId && nextShardId !== selectedShardId) {
        selectShard(nextShardId);
      }
    },
    [orderedShardIds, selectShard, selectedShardId],
  );

  const refreshAll = useCallback(() => {
    setRefreshNonce((value) => value + 1);
  }, []);
  const activateBrowseSection = useCallback(
    (section: ShardBrowseSection) => {
      if (!section.action) return;
      if (section.action.kind === 'group') {
        setFilter({ group: section.action.value, paragraph: '' });
        return;
      }
      if (section.action.kind === 'paragraph') {
        setFilter({ paragraph: section.action.value });
        return;
      }
      openDrill(section.action.target);
    },
    [openDrill, setFilter],
  );

  return (
    <div
      data-zenith-shards-surface={surfaceReady || shardsBudgetElapsed ? 'ready' : undefined}
      className="grid min-h-0 flex-1 grid-cols-12 gap-[var(--zenith-space-2-5)]"
    >
      <section className="panel col-span-12">
        <PanelHead
          kicker="Shards"
          title={
            overview?.source_path
              ? `${overview.source.replace('_', ' ')} shard substrate`
              : 'Queryable shard substrate'
          }
          trailing={
            <div className="flex items-center gap-1.5">
              {overview && <FreshnessBadge freshness={overview.freshness} compact />}
              <button
                type="button"
                onClick={refreshAll}
                className="inline-flex items-center gap-1 rounded-full border border-zenith-edge bg-black/20 px-2 py-0.5 font-mono text-[9px] uppercase tracking-[0.18em] text-zenith-soft transition-colors hover:border-white/30 hover:text-white"
                title="Re-run overview/query/detail fetches"
              >
                <RefreshCw size={10} />
                refresh
              </button>
            </div>
          }
        />
        <div className="panel-body-padded flex flex-col gap-[var(--zenith-space-2-5)]">
          <div className="flex flex-wrap items-center gap-1.5">
            {SHARD_SOURCES.map((value) => (
              <button
                key={value}
                type="button"
                onClick={() => selectSource(value)}
                className={clsx(
                  'rounded-full border px-[var(--zenith-space-2-5)] py-1 font-mono text-[10px] uppercase tracking-[0.18em] transition-colors',
                  source === value
                    ? 'border-[var(--zenith-accent-edge)] bg-[var(--zenith-accent-soft)] text-[var(--zenith-accent)]'
                    : 'border-zenith-edge bg-black/20 text-zenith-soft hover:border-white/20 hover:text-white',
                )}
              >
                {value.replace('_', ' ')}
              </button>
            ))}
            <span
              className="min-w-0 flex-1 truncate rounded-full border border-zenith-edge bg-black/20 px-[var(--zenith-space-2-5)] py-1 font-mono text-[10px] uppercase tracking-[0.18em] text-white/55"
              title={overview?.source_path ?? 'Shard world-model source path pending'}
            >
              {overview?.source_path ?? 'Resolving source path…'}
            </span>
          </div>

          <StateGuard
            data={overview}
            loading={overviewLoading}
            error={routeMismatchError ? null : overviewError}
            emptyLabel={
              routeMismatchError
                ? 'Shard routes unavailable from the running backend.'
                : 'No shard overview available.'
            }
            onRetry={refreshAll}
          >
            {(data) => (
              <div className="flex flex-wrap items-center gap-1.5">
                <HeaderStatPill label="shards" value={data.total_shards.toLocaleString()} />
                <HeaderStatPill label="groups" value={data.total_groups.toLocaleString()} />
                <HeaderStatPill
                  label="pending"
                  value={data.pending_count.toLocaleString()}
                  tone={data.pending_count > 0 ? 'warn' : 'ok'}
                />
                {data.surface_kind && (
                  <HeaderStatPill label="surface" value={data.surface_kind} tone="muted" />
                )}
                {query && (
                  <FilterChip
                    icon={<Search size={10} />}
                    label={query}
                    onClear={() => setFilter({ query: '' })}
                  />
                )}
                {group && (
                  <FilterChip
                    icon={<Hash size={10} />}
                    label={group}
                    onClear={() => setFilter({ group: '' })}
                  />
                )}
                {paragraphId && (
                  <FilterChip
                    icon={<Quote size={10} />}
                    label={paragraphId}
                    onClear={() => setFilter({ paragraph: '' })}
                  />
                )}
                {status && (
                  <FilterChip
                    icon={<Filter size={10} />}
                    label={status}
                    onClear={() => setFilter({ status: '' })}
                  />
                )}
              </div>
            )}
          </StateGuard>
        </div>
      </section>

      {routeMismatchError ? (
        <section className="panel col-span-12">
          <PanelHead kicker="Route mismatch" title="Running backend is missing shard routes" />
          <div className="panel-body-padded">
            <div className="rounded-[var(--zenith-radius-region)] border border-amber-400/30 bg-amber-500/10 px-4 py-4 text-amber-100">
              <div className="font-mono text-[11px] uppercase tracking-[0.2em] text-amber-200">
                shard endpoints unavailable
              </div>
              <p className="mt-2 max-w-3xl text-[13px] leading-6 text-amber-50">
                The running backend does not currently expose the read-only shard lens routes.
                Restart the backend serving <span className="font-mono">/api/world-model/shards/*</span>,
                then reload this lens.
              </p>
              <div className="mt-2 rounded-[var(--zenith-radius-md)] border border-amber-400/20 bg-black/20 px-3 py-2 font-mono text-[11px] leading-5 text-amber-100/90">
                {routeMismatchError instanceof Error
                  ? routeMismatchError.message
                  : routeMismatchError}
              </div>
              <div className="mt-3 flex flex-wrap gap-1.5">
                <button
                  type="button"
                  onClick={refreshAll}
                  className="inline-flex items-center gap-1.5 rounded-full border border-amber-300/40 bg-amber-500/10 px-3 py-1 font-mono text-[10px] uppercase tracking-[0.18em] text-amber-100 hover:border-amber-200/60"
                >
                  <RefreshCw size={11} />
                  retry
                </button>
              </div>
            </div>
          </div>
        </section>
      ) : (
        <>
      <section className="panel col-span-12 lg:col-span-4 xl:col-span-3">
        <PanelHead
          kicker="Query"
          title={
            results
              ? `${results.matched.toLocaleString()} / ${results.total_in_pool.toLocaleString()}`
              : 'Filters'
          }
          trailing={results ? <FreshnessBadge freshness={results.freshness} compact /> : undefined}
        />
        <div className="panel-body-padded flex min-h-0 flex-col gap-[var(--zenith-space-2-5)]">
          <form
            className="grid gap-1.5"
            onSubmit={(event) => {
              event.preventDefault();
              applyFilters();
            }}
          >
              <FilterInput
                icon={<Search size={11} className="opacity-60" />}
                kicker="Query"
                value={activeDraftFilters.query}
                onChange={(value) => setDraftField('query', value)}
                placeholder="voice, gesture, topic"
              />
            <div className="grid gap-1.5 md:grid-cols-2">
              <FilterInput
                icon={<Hash size={11} className="opacity-60" />}
                kicker="Group"
                value={activeDraftFilters.group}
                onChange={(value) => setDraftField('group', value)}
                placeholder="grp_*"
              />
              <FilterInput
                icon={<Quote size={11} className="opacity-60" />}
                kicker="Paragraph"
                value={activeDraftFilters.paragraphId}
                onChange={(value) => setDraftField('paragraphId', value)}
                placeholder="par_*"
              />
            </div>
            <FilterInput
              icon={<Filter size={11} className="opacity-60" />}
              kicker="Status / state"
              value={activeDraftFilters.status}
              onChange={(value) => setDraftField('status', value)}
              placeholder="pending / addressed / needs_codex"
            />
            <div className="flex flex-wrap gap-1.5">
              <button
                type="submit"
                className="inline-flex items-center gap-1.5 rounded-full border border-[var(--zenith-accent-edge)] bg-[var(--zenith-accent-soft)] px-3 py-1 font-mono text-[10px] uppercase tracking-[0.18em] text-[var(--zenith-accent)] hover:brightness-125"
              >
                <Search size={11} />
                apply
              </button>
              <button
                type="button"
                onClick={clearFilters}
                className="rounded-full border border-zenith-edge bg-black/20 px-3 py-1 font-mono text-[10px] uppercase tracking-[0.18em] text-zenith-soft hover:border-white/25 hover:text-white"
              >
                clear
              </button>
            </div>
          </form>

          {overview && (
            <div className="grid gap-1.5">
              <CompactFacetBlock title="Top gestures" empty="No gestures recorded yet.">
                {overview.top_gestures.slice(0, 4).map((facet) => (
                  <button
                    key={facet.value}
                    type="button"
                    onClick={() => setFilter({ query: facet.value })}
                    className="rounded-full border border-zenith-edge bg-white/[0.04] px-2 py-0.5 font-mono text-[10px] text-white/75 transition-colors hover:border-white/30 hover:text-white"
                    title="Query by this gesture"
                  >
                    {facet.value}
                    <span className="ml-1 text-zenith-muted">· {facet.count}</span>
                  </button>
                ))}
              </CompactFacetBlock>
              <CompactFacetBlock title="Authority hints" empty="No doctrine anchors captured yet.">
                {overview.top_doctrine_targets.slice(0, 4).map((facet) => (
                  <AuthorityChip
                    key={`${facet.kind}:${facet.id}`}
                    kind={doctrineKind(facet.kind)}
                    target={facet.id}
                    label={facet.title ?? facet.id}
                    onClick={() => {
                      const kind: DoctrineDrillDownKind =
                        facet.kind === 'mechanism'
                          ? 'mechanism'
                          : facet.kind === 'principle'
                            ? 'principle'
                            : 'concept';
                      openDrill({ kind, target: facet.id });
                    }}
                    compact
                  />
                ))}
                {overview.top_files.slice(0, 3).map((facet) => (
                  <span
                    key={facet.value}
                    className="inline-flex items-center gap-1 rounded-full border border-zenith-edge bg-white/[0.04] px-2 py-0.5 font-mono text-[10px] text-zenith-soft"
                    title={facet.value}
                  >
                    <FileCode2 size={10} className="opacity-60" />
                    {fileLabel(facet.value)}
                    <span className="text-zenith-muted">· {facet.count}</span>
                  </span>
                ))}
              </CompactFacetBlock>
            </div>
          )}

          {results && (results.filters.group || results.filters.paragraph_id || results.filters.status) && (
            <div className="flex flex-wrap gap-1">
              {results.filters.group && (
                <FilterChip
                  icon={<Hash size={10} />}
                  label={results.filters.group}
                  onClear={() => setFilter({ group: '' })}
                />
              )}
              {results.filters.paragraph_id && (
                <FilterChip
                  icon={<Quote size={10} />}
                  label={results.filters.paragraph_id}
                  onClear={() => setFilter({ paragraph: '' })}
                />
              )}
              {results.filters.status && (
                <FilterChip
                  icon={<Filter size={10} />}
                  label={results.filters.status}
                  onClear={() => setFilter({ status: '' })}
                />
              )}
            </div>
          )}

          {browseSections.some((section) => section.action) && (
            <CompactFacetBlock title="Neighborhood browse" empty="No shard neighborhoods detected yet.">
              {browseSections
                .filter((section) => section.action)
                .slice(0, 8)
                .map((section) => (
                  <BrowseSectionPill
                    key={section.key}
                    section={section}
                    onClick={() => activateBrowseSection(section)}
                  />
                ))}
            </CompactFacetBlock>
          )}

          <div
            ref={resultListRef}
            onKeyDown={handleResultKey}
            tabIndex={0}
            role="listbox"
            aria-label="Shard results"
            className="min-h-0 flex-1 overflow-y-auto rounded-[var(--zenith-radius-lg)] border border-zenith-edge focus:outline-none focus-visible:ring-1 focus-visible:ring-[var(--zenith-accent-edge)]"
          >
            <StateGuard
              data={results}
              loading={resultsLoading}
              error={resultsError}
              emptyLabel="No shard results yet."
              onRetry={refreshAll}
              className="m-2"
            >
              {(data) => (
                <div className="space-y-2 p-2">
                  {browseSections.length === 0 ? (
                    <div className="px-3 py-3 text-[12px] text-[var(--zenith-soft)]">
                      No results for the current filter set.
                    </div>
                  ) : (
                    browseSections.map((section) => (
                      <ResultSection
                        key={section.key}
                        section={section}
                        selectedShardId={selectedShardId}
                        maxScore={maxResultScore}
                        onSectionAction={() => activateBrowseSection(section)}
                        onSelectShard={selectShard}
                      />
                    ))
                  )}
                  {data.related.length > 0 && (
                    <RelatedGroup
                      related={data.related}
                      selectedShardId={selectedShardId}
                      onSelect={selectShard}
                    />
                  )}
                </div>
              )}
            </StateGuard>
          </div>
        </div>
      </section>

      <section className="panel col-span-12 lg:col-span-4 xl:col-span-5">
        <PanelHead
          kicker="Relationships"
          title={
            graph
              ? `${graph.nodes.length} nodes · ${graph.edges.length} edges`
              : 'No graph projection'
          }
          trailing={detail ? <FreshnessBadge freshness={detail.freshness} compact /> : undefined}
        />
        <div className="flex min-h-0 flex-1 flex-col gap-2 px-3 py-2">
          <ShardGraphLegend className="flex-shrink-0" />
          {results && results.matched === 0 && (query || group || paragraphId || status) ? (
            <FilteredEmptyGraphCard
              source={source}
              query={query}
              group={group}
              paragraphId={paragraphId}
              status={status}
              onClearFilters={clearFilters}
              onRefresh={refreshAll}
            />
          ) : (
            <StateGuard
              data={graph}
              loading={graphLoading}
              error={graphError}
              emptyLabel="Select a shard to load its neighborhood graph."
              className="m-1"
            >
              {(data) => (
                <div className="flex min-h-[360px] flex-1">
                  <ShardGraph
                    graph={data}
                    selection={{ shardId: selectedShardId || undefined }}
                    onNodeSelect={handleGraphNode}
                  />
                </div>
              )}
            </StateGuard>
          )}
        </div>
      </section>

      <section className="panel col-span-12 lg:col-span-4 xl:col-span-4">
        <PanelHead
          kicker="Detail"
          title={selectedShardId || 'Pick a shard'}
          trailing={detail ? <FreshnessBadge freshness={detail.freshness} compact /> : undefined}
        />
        <div className="panel-body-padded flex min-h-0 flex-col">
          {detail ? (
            <ShardDetailBody
              detail={detail}
              mapScroll={mapScroll}
              onOpenRoute={openSurfaceRoute}
              onSelectShard={selectShard}
              onFilter={setFilter}
              onOpenDrill={openDrill}
              onOpenFile={openFileSurface}
              selectedShardId={selectedShardId}
            />
          ) : selectedResult && !detailError ? (
            <ShardDetailPreview
              result={selectedResult}
              loading={detailLoading}
              onRetry={refreshAll}
            />
          ) : (
            <StateGuard<ShardLensDetailResponse>
              data={selectedShardId ? detail : null}
              loading={detailLoading}
              error={detailError}
              emptyLabel="Pick a shard to inspect voice anchor, routing targets, and provenance."
              onRetry={refreshAll}
            >
              {(data) => (
                <ShardDetailBody
                  detail={data}
                  mapScroll={mapScroll}
                  onOpenRoute={openSurfaceRoute}
                  onSelectShard={selectShard}
                  onFilter={setFilter}
                  onOpenDrill={openDrill}
                  onOpenFile={openFileSurface}
                  selectedShardId={selectedShardId}
                />
              )}
            </StateGuard>
          )}
        </div>
      </section>
        </>
      )}

      {drill && (
        <DoctrineDrillDown kind={drill.kind} target={drill.target} onClose={closeDrill} />
      )}
    </div>
  );
}

function HeaderStatPill({
  label,
  value,
  tone = 'muted',
}: {
  label: string;
  value: string;
  tone?: 'ok' | 'warn' | 'muted';
}) {
  return (
    <span
      className={clsx(
        'inline-flex items-center gap-1.5 rounded-full border px-[var(--zenith-space-2-5)] py-1 font-mono text-[10px] uppercase tracking-[0.18em]',
        tone === 'ok' && 'border-emerald-400/25 bg-emerald-500/8 text-emerald-100',
        tone === 'warn' && 'border-amber-400/30 bg-amber-500/10 text-amber-100',
        tone === 'muted' && 'border-zenith-edge bg-black/20 text-zenith-soft',
      )}
    >
      <span className="text-white/45">{label}</span>
      <span className="text-white">{value}</span>
    </span>
  );
}

function CompactFacetBlock({
  title,
  empty,
  children,
}: {
  title: string;
  empty: string;
  children: ReactNode;
}) {
  const childArray = Array.isArray(children) ? children : [children];
  const hasChildren = childArray.filter(Boolean).length > 0;
  return (
    <div className="rounded-[var(--zenith-radius-md)] border border-zenith-edge bg-black/20 px-3 py-2">
      <div className="panel-kicker">{title}</div>
      <div className="mt-1.5 flex flex-wrap gap-1">
        {hasChildren ? children : <span className="text-[11px] text-[var(--zenith-soft)]">{empty}</span>}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Query-pane sub-presentation
// ---------------------------------------------------------------------------

// When a filter set matches zero shards, the relationship graph has no payload.
// Rather than leave the canvas a blank void (which reads as "broken"), explain
// *why* it is empty and offer the next action (clear filters / refresh) right
// inside the graph region. Per the selected-route topology focus wave.
function FilteredEmptyGraphCard({
  source,
  query,
  group,
  paragraphId,
  status,
  onClearFilters,
  onRefresh,
}: {
  source: string;
  query: string;
  group: string;
  paragraphId: string;
  status: string;
  onClearFilters: () => void;
  onRefresh: () => void;
}) {
  const activeFilters = [
    { label: 'source', value: source },
    { label: 'query', value: query },
    { label: 'group', value: group },
    { label: 'paragraph', value: paragraphId },
    { label: 'status', value: status },
  ].filter((entry) => entry.value);
  return (
    <div
      data-zenith-shard-graph-filtered-empty="true"
      className="flex min-h-[360px] flex-1 items-center justify-center rounded-[var(--zenith-radius-lg)] border border-zenith-edge bg-[var(--zenith-bg-deep)]"
    >
      <div className="max-w-sm rounded-[var(--zenith-radius-region)] border border-zenith-edge bg-black/40 px-5 py-4 text-center">
        <div className="mx-auto flex h-9 w-9 items-center justify-center rounded-full border border-zenith-edge bg-white/[0.03]">
          <Filter size={15} className="text-[var(--zenith-accent)]" />
        </div>
        <div className="mt-2 font-mono text-[11px] uppercase tracking-[0.18em] text-zenith-soft">
          No shards match this filter set
        </div>
        <p className="mt-1 text-[12px] leading-5 text-[var(--zenith-muted)]">
          The relationship graph is empty because nothing passed the active filters — not because the substrate is empty.
        </p>
        {activeFilters.length > 0 && (
          <div className="mt-3 flex flex-wrap justify-center gap-1">
            {activeFilters.map((entry) => (
              <span
                key={entry.label}
                className="inline-flex items-center gap-1 rounded-full border border-[var(--zenith-accent-edge)] bg-[var(--zenith-accent-soft)] px-2 py-0.5 font-mono text-[9px] uppercase tracking-[0.16em] text-[var(--zenith-accent)]"
              >
                {entry.label}: {entry.value}
              </span>
            ))}
          </div>
        )}
        <div className="mt-3 flex flex-wrap justify-center gap-1.5">
          <button
            type="button"
            onClick={onClearFilters}
            className="inline-flex items-center gap-1.5 rounded-full border border-[var(--zenith-accent-edge)] bg-[var(--zenith-accent-soft)] px-3 py-1 font-mono text-[10px] uppercase tracking-[0.18em] text-[var(--zenith-accent)] transition-colors hover:brightness-125 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--zenith-accent)]"
          >
            <X size={11} />
            clear filters
          </button>
          <button
            type="button"
            onClick={onRefresh}
            className="inline-flex items-center gap-1.5 rounded-full border border-zenith-edge bg-black/20 px-3 py-1 font-mono text-[10px] uppercase tracking-[0.18em] text-zenith-soft transition-colors hover:border-white/25 hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--zenith-accent)]"
          >
            <RefreshCw size={11} />
            refresh
          </button>
        </div>
      </div>
    </div>
  );
}

function FilterInput({
  icon,
  kicker,
  value,
  onChange,
  placeholder,
}: {
  icon: ReactNode;
  kicker: string;
  value: string;
  onChange: (next: string) => void;
  placeholder?: string;
}) {
  return (
    <label className="rounded-[var(--zenith-radius-md)] border border-zenith-edge bg-black/20 px-[var(--zenith-space-2-5)] py-1.5 transition-colors focus-within:border-[var(--zenith-accent-edge)]">
      <div className="flex items-center gap-1 panel-kicker">
        {icon}
        <span>{kicker}</span>
      </div>
      <input
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
        className="mt-0.5 w-full bg-transparent font-mono text-[11.5px] text-white outline-none placeholder:text-white/35"
      />
    </label>
  );
}

function FilterChip({
  icon,
  label,
  onClear,
}: {
  icon: ReactNode;
  label: string;
  onClear: () => void;
}) {
  return (
    <span className="inline-flex items-center gap-1 rounded-full border border-[var(--zenith-accent-edge)] bg-[var(--zenith-accent-soft)] px-2 py-0.5 font-mono text-[10px] uppercase tracking-[0.16em] text-[var(--zenith-accent)]">
      {icon}
      <span>{label}</span>
      <button
        type="button"
        onClick={onClear}
        className="-mr-0.5 ml-0.5 rounded-full hover:bg-white/10"
        aria-label={`Clear ${label}`}
      >
        <X size={10} />
      </button>
    </span>
  );
}

function BrowseSectionPill({
  section,
  onClick,
}: {
  section: ShardBrowseSection;
  onClick: () => void;
}) {
  const actionable = Boolean(section.action);
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={!actionable}
      className={clsx(
        'inline-flex items-center gap-1 rounded-full border px-2 py-0.5 font-mono text-[10px] uppercase tracking-[0.16em] transition-colors',
        actionable
          ? 'border-zenith-edge bg-white/[0.04] text-white/75 hover:border-white/30 hover:text-white'
          : 'cursor-default border-white/5 bg-black/20 text-zenith-muted',
      )}
      title={section.action?.label ?? section.kicker}
    >
      {section.kind === 'group' && <Hash size={9} />}
      {section.kind === 'paragraph' && <Quote size={9} />}
      {section.kind === 'routing' && <Target size={9} />}
      {section.kind === 'standalone' && <Waypoints size={9} />}
      <span>{section.label}</span>
      <span className="text-zenith-muted">· {section.results.length}</span>
    </button>
  );
}

function ResultRow({
  result,
  active,
  maxScore,
  onSelect,
}: {
  result: ShardQueryResult;
  active: boolean;
  maxScore: number;
  onSelect: () => void;
}) {
  const shard = result.shard;
  const status = shardStatus(shard);
  const gestures = asStringArray(shard.gestures_towards);
  const groups = asStringArray(shard.idea_group_ids);
  return (
    <button
      type="button"
      onClick={onSelect}
      aria-selected={active}
      role="option"
      className={clsx(
        'flex w-full flex-col gap-1 px-3 py-[var(--zenith-space-2-5)] text-left transition-colors',
        active ? 'bg-white/[0.08]' : 'hover:bg-white/[0.04]',
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-1.5">
            <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-white/50">
              {result.shard_id}
            </span>
            {status.routing && (
              <LifecycleChip
                status={stateTone(status.routing) === 'warn' ? 'blocked' : 'success'}
                label={status.routing}
                compact
              />
            )}
          </div>
          <div className="mt-1 text-[12px] leading-5 text-white line-clamp-3">
            {shardLabel(shard)}
          </div>
        </div>
        <div className="shrink-0 text-right font-mono text-[10px] text-white/50">
          {result.score > 0 ? `score ${result.score}` : 'structural'}
        </div>
      </div>
      <MatchedAxesBar axes={result.matched_axes} maxScore={maxScore} />
      {(groups.length > 0 || gestures.length > 0) && (
        <div className="mt-0.5 flex flex-wrap gap-1">
          {groups.slice(0, 3).map((groupId, index) => (
            <span
              key={`g:${groupId}:${index}`}
              className="inline-flex items-center gap-1 rounded-full border border-zenith-edge bg-white/[0.04] px-2 py-0.5 font-mono text-[9px] uppercase tracking-[0.18em] text-white/60"
            >
              <Hash size={8} />
              {groupId}
            </span>
          ))}
          {gestures.slice(0, 2).map((gesture, index) => (
            <span
              key={`w:${gesture}:${index}`}
              className="inline-flex items-center gap-1 rounded-full border border-zenith-edge bg-white/[0.04] px-2 py-0.5 font-mono text-[9px] uppercase tracking-[0.18em] text-white/60"
            >
              <Waypoints size={8} />
              {gesture}
            </span>
          ))}
        </div>
      )}
    </button>
  );
}

function ResultSection({
  section,
  selectedShardId,
  maxScore,
  onSectionAction,
  onSelectShard,
}: {
  section: ShardBrowseSection;
  selectedShardId: string;
  maxScore: number;
  onSectionAction: () => void;
  onSelectShard: (shardId: string) => void;
}) {
  return (
    <section className="overflow-hidden rounded-[var(--zenith-radius-md)] border border-zenith-edge bg-black/20">
      <div className="sticky top-0 z-10 flex items-center gap-2 border-b border-white/8 bg-[var(--zenith-panel)]/95 px-3 py-1.5 backdrop-blur">
        <span className="panel-kicker">{section.kicker}</span>
        <span className="min-w-0 truncate font-mono text-[10px] uppercase tracking-[0.16em] text-zenith-soft">
          {section.label}
        </span>
        <span className="ml-auto shrink-0 font-mono text-[10px] tabular-nums text-white/45">
          {section.results.length}
        </span>
        {section.action && (
          <button
            type="button"
            onClick={onSectionAction}
            className="shrink-0 rounded-full border border-zenith-edge bg-black/20 px-2 py-0.5 font-mono text-[9px] uppercase tracking-[0.16em] text-white/65 transition-colors hover:border-white/25 hover:text-white"
          >
            {section.action.label}
          </button>
        )}
      </div>
      <div className="panel-divide">
        {section.results.map((result) => (
          <ResultRow
            key={result.shard_id}
            result={result}
            active={result.shard_id === selectedShardId}
            maxScore={maxScore}
            onSelect={() => onSelectShard(result.shard_id)}
          />
        ))}
      </div>
    </section>
  );
}

function RelatedGroup({
  related,
  selectedShardId,
  onSelect,
}: {
  related: ShardRelatedResult[];
  selectedShardId: string;
  onSelect: (shardId: string) => void;
}) {
  return (
    <div className="rounded-[var(--zenith-radius-md)] border border-zenith-edge bg-black/20 px-3 py-2">
      <div className="panel-kicker mb-1.5">
        Nearby hops · {related.length.toLocaleString()}
      </div>
      <div className="flex flex-wrap gap-1">
        {related.slice(0, 12).map((entry) => {
          const active = entry.shard_id === selectedShardId;
          const kinds = entry.related_by
            .map((edge) => asString(edge.kind))
            .filter(Boolean);
          return (
            <button
              key={entry.shard_id}
              type="button"
              onClick={() => onSelect(entry.shard_id)}
              className={clsx(
                'rounded-full border px-2 py-0.5 font-mono text-[10px] transition-colors',
                active
                  ? 'border-[var(--zenith-accent-edge)] bg-[var(--zenith-accent-soft)] text-[var(--zenith-accent)]'
                  : 'border-zenith-edge bg-black/20 text-zenith-soft hover:border-white/25 hover:text-white',
              )}
              title={kinds.join(' · ') || 'related shard'}
            >
              {entry.shard_id}
              <span className="ml-1 text-zenith-muted">{kinds[0] ?? 'related'}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Detail-pane sub-presentation
// ---------------------------------------------------------------------------

interface ShardDetailBodyProps {
  detail: ShardLensDetailResponse;
  mapScroll: MapScrollLayout;
  onOpenRoute: (route: string, label: string) => void;
  onSelectShard: (shardId: string) => void;
  onFilter: (partial: {
    group?: string;
    paragraph?: string;
    status?: string;
    query?: string;
  }) => void;
  onOpenDrill: (target: DrillTarget) => void;
  onOpenFile: (path: string) => void;
  selectedShardId: string;
}

function ShardDetailPreview({
  result,
  loading,
  onRetry,
}: {
  result: ShardQueryResult | ShardRelatedResult;
  loading: boolean;
  onRetry: () => void;
}) {
  const shard = result.shard;
  const statement = shardLabel(shard);
  const voiceAnchor = asString(shard.voice_anchor);
  const groups = asStringArray(shard.idea_group_ids);
  const gestures = asStringArray(shard.gestures_towards);
  const routingTargets = extractRoutingTargets(shard);
  const parentParagraphId = asString(shard.parent_paragraph_id);
  const routingState = asString(shard.routing_state);
  const coverageState = asString(shard.coverage_state);

  return (
    <div
      className="flex min-h-0 flex-1 flex-col gap-3 overflow-y-auto pr-1"
      data-zenith-shard-detail-preview={result.shard_id}
      data-zenith-shard-detail-preview-loading={loading ? 'true' : 'false'}
    >
      {loading && (
        <div className="rounded-[var(--zenith-radius-md)] border border-[var(--zenith-accent-edge)] bg-[var(--zenith-accent-soft)] px-3 py-2 font-mono text-[10px] uppercase tracking-[0.16em] text-[var(--zenith-accent)]">
          detail endpoint still resolving · showing query projection
        </div>
      )}
      <section className="rounded-[var(--zenith-radius-lg)] border border-zenith-edge bg-black/25 px-3 py-3">
        <div className="panel-kicker">Selected shard preview</div>
        <p className="mt-1.5 text-[13px] leading-6 text-white">{statement}</p>
        {voiceAnchor && (
          <blockquote className="mt-3 rounded-[var(--zenith-radius-sm)] border-l-2 border-[var(--zenith-accent)] bg-white/[0.03] px-3 py-2">
            <div className="flex items-center gap-1 panel-kicker">
              <Quote size={10} />
              <span>Voice anchor</span>
            </div>
            <p className="mt-1 font-mono text-[12px] italic leading-5 text-white/90">
              "{voiceAnchor}"
            </p>
          </blockquote>
        )}
      </section>
      <section className="rounded-[var(--zenith-radius-lg)] border border-zenith-edge bg-black/25 px-3 py-[var(--zenith-space-2-5)]">
        <div className="grid gap-2 sm:grid-cols-2">
          <ProvenanceRow label="Routing">
            <span className="text-zenith-soft">{routingState || 'unprojected'}</span>
          </ProvenanceRow>
          <ProvenanceRow label="Coverage">
            <span className="text-zenith-soft">{coverageState || 'unprojected'}</span>
          </ProvenanceRow>
          {parentParagraphId && (
            <ProvenanceRow label="Parent paragraph">
              <span className="font-mono text-[11px] text-white/75">{parentParagraphId}</span>
            </ProvenanceRow>
          )}
          <ProvenanceRow label="Score">
            <span className="font-mono text-[11px] text-white/75">{result.score.toFixed(2)}</span>
          </ProvenanceRow>
        </div>
        {(groups.length > 0 || gestures.length > 0 || routingTargets.length > 0) && (
          <div className="mt-3 flex flex-wrap gap-1.5">
            {groups.slice(0, 6).map((groupId) => (
              <PreviewChip key={`group:${groupId}`} tone="cyan">#{groupId}</PreviewChip>
            ))}
            {gestures.slice(0, 6).map((gesture) => (
              <PreviewChip key={`gesture:${gesture}`} tone="amber">{gesture}</PreviewChip>
            ))}
            {routingTargets.slice(0, 4).map((target) => (
              <PreviewChip key={`target:${target.target_id}`} tone="purple">{target.kind}: {target.target_id}</PreviewChip>
            ))}
          </div>
        )}
      </section>
      <button
        type="button"
        onClick={onRetry}
        className="inline-flex w-fit items-center gap-1 rounded-full border border-zenith-edge bg-black/20 px-2 py-1 font-mono text-[10px] uppercase tracking-[0.16em] text-zenith-soft transition-colors hover:border-white/25 hover:text-white"
      >
        <RefreshCw size={11} />
        retry detail
      </button>
    </div>
  );
}

function PreviewChip({
  children,
  tone,
}: {
  children: ReactNode;
  tone: 'amber' | 'cyan' | 'purple';
}) {
  return (
    <span
      className={clsx(
        'rounded-full border px-2 py-0.5 font-mono text-[10px] uppercase tracking-[0.14em]',
        tone === 'amber' && 'border-amber-300/25 bg-amber-300/[0.08] text-amber-100/80',
        tone === 'cyan' && 'border-cyan-300/25 bg-cyan-300/[0.08] text-cyan-100/80',
        tone === 'purple' && 'border-violet-300/25 bg-violet-300/[0.08] text-violet-100/80',
      )}
    >
      {children}
    </span>
  );
}

function ShardDetailBody({
  detail,
  mapScroll,
  onOpenRoute,
  onSelectShard,
  onFilter,
  onOpenDrill,
  onOpenFile,
}: ShardDetailBodyProps) {
  const target = detail.target;
  const gestures = asStringArray(target.gestures_towards);
  const groups = asStringArray(target.idea_group_ids);
  const routingTargets = extractRoutingTargets(target);
  const relevantFiles = asStringArray(target.relevant_files);
  const voiceAnchor = asString(target.voice_anchor);
  const supportExcerpt = asString(target.support_excerpt);
  const parentParagraphId = asString(target.parent_paragraph_id);
  const sourceArtifact = asString(target.source_artifact);
  const sourceBinId = asString(target.source_bin_id);
  const routingState = asString(target.routing_state);
  const coverageState = asString(target.coverage_state);
  const segment = asString(target.segment_ordinal);

  const neighborhood = detail.neighborhood as {
    before?: Array<Record<string, unknown>>;
    after?: Array<Record<string, unknown>>;
  };
  const before = asRecordArray(neighborhood.before);
  const after = asRecordArray(neighborhood.after);

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-3 overflow-y-auto pr-1">
      <MapScroll
        layout={mapScroll}
        onOpenRoute={onOpenRoute}
        emptyLabel="No navigation graph packet is available on this shard surface yet."
      />

      {/* Statement + voice anchor */}
      <section className="rounded-[var(--zenith-radius-lg)] border border-zenith-edge bg-black/25 px-3 py-3">
        <div className="flex items-center gap-1.5">
          <div className="panel-kicker">Clarified statement</div>
          {segment && <span className="panel-kicker text-zenith-muted">· seg {segment}</span>}
        </div>
        <p className="mt-1.5 text-[13px] leading-6 text-white">{shardLabel(target)}</p>
        {voiceAnchor && (
          <blockquote className="mt-3 rounded-[var(--zenith-radius-sm)] border-l-2 border-[var(--zenith-accent)] bg-white/[0.03] px-3 py-2">
            <div className="flex items-center gap-1 panel-kicker">
              <Quote size={10} />
              <span>Voice anchor</span>
            </div>
            <p className="mt-1 font-mono text-[12px] italic leading-5 text-white/90">
              “{voiceAnchor}”
            </p>
          </blockquote>
        )}
        {supportExcerpt && supportExcerpt !== voiceAnchor && (
          <div className="mt-2 rounded-[var(--zenith-radius-sm)] border border-zenith-edge bg-white/[0.02] px-3 py-2">
            <div className="panel-kicker">Support excerpt</div>
            <p className="mt-1 font-mono text-[11.5px] leading-5 text-[var(--zenith-soft)]">
              {supportExcerpt}
            </p>
          </div>
        )}
      </section>

      {/* State + facets */}
      <section className="rounded-[var(--zenith-radius-lg)] border border-zenith-edge bg-black/25 px-3 py-[var(--zenith-space-2-5)]">
        <div className="panel-kicker">Facets</div>
        <div className="mt-2 flex flex-wrap gap-1">
          {routingState &&
            tonefulBadge({
              tone: stateTone(routingState),
              children: <>routing · {routingState}</>,
            })}
          {coverageState &&
            tonefulBadge({
              tone: stateTone(coverageState),
              children: <>coverage · {coverageState}</>,
            })}
          {groups.map((groupId) => (
            <AuthorityChip
              key={groupId}
              kind="doc"
              target={groupId}
              label={`grp ${groupId}`}
              onClick={() => onFilter({ group: groupId, paragraph: '' })}
              compact
            />
          ))}
          {gestures.map((gesture) => (
            <span
              key={gesture}
              className="inline-flex items-center gap-1 rounded-full border border-zenith-edge bg-white/[0.04] px-2 py-0.5 font-mono text-[10px] text-white/80"
              title="gestures_towards"
            >
              <Waypoints size={10} className="opacity-60" />
              {gesture}
            </span>
          ))}
          {groups.length === 0 && gestures.length === 0 && !routingState && !coverageState && (
            <span className="text-[11px] text-[var(--zenith-soft)]">No facets on this shard.</span>
          )}
        </div>
      </section>

      {/* Routing targets */}
      <section className="rounded-[var(--zenith-radius-lg)] border border-zenith-edge bg-black/25 px-3 py-[var(--zenith-space-2-5)]">
        <div className="flex items-center gap-1 panel-kicker">
          <Target size={10} />
          <span>Routing targets</span>
          <span className="ml-auto text-zenith-muted">{routingTargets.length}</span>
        </div>
        <div className="mt-2 flex flex-wrap gap-1">
          {routingTargets.length === 0 ? (
            <span className="text-[11px] text-[var(--zenith-soft)]">
              No routing targets captured on this shard.
            </span>
          ) : (
            routingTargets.map((route) => (
              <AuthorityChip
                key={`${route.kind}:${route.target_id}`}
                kind={doctrineKind(route.kind)}
                target={route.target_id}
                label={route.target_id}
                onClick={() => {
                  const kind: DoctrineDrillDownKind =
                    route.kind === 'mechanism'
                      ? 'mechanism'
                      : route.kind === 'principle'
                        ? 'principle'
                        : 'concept';
                  onOpenDrill({ kind, target: route.target_id });
                }}
                compact
              />
            ))
          )}
          {detail.doctrine_refs
            .filter(
              (ref) =>
                !routingTargets.some((rt) => rt.target_id === ref.id && rt.kind === ref.kind),
            )
            .map((ref) => (
              <AuthorityChip
                key={`${ref.kind}:${ref.id}`}
                kind={doctrineKind(ref.kind)}
                target={ref.id}
                label={ref.title ?? ref.id}
                onClick={() => {
                  const kind: DoctrineDrillDownKind =
                    ref.kind === 'mechanism'
                      ? 'mechanism'
                      : ref.kind === 'principle'
                        ? 'principle'
                        : 'concept';
                  onOpenDrill({ kind, target: ref.id });
                }}
                compact
              />
            ))}
        </div>
      </section>

      {/* Provenance */}
      <section className="rounded-[var(--zenith-radius-lg)] border border-zenith-edge bg-black/25 px-3 py-[var(--zenith-space-2-5)]">
        <div className="panel-kicker">Provenance</div>
        <dl className="mt-2 grid gap-1.5 text-[11.5px] text-[var(--zenith-soft)]">
          {parentParagraphId && (
            <ProvenanceRow label="Parent paragraph">
              <AuthorityChip
                kind="raw_seed_paragraph"
                target={parentParagraphId}
                label={parentParagraphId}
                onClick={() =>
                  onOpenDrill({ kind: 'raw_seed_paragraph', target: parentParagraphId })
                }
                compact
              />
              <button
                type="button"
                onClick={() => onFilter({ paragraph: parentParagraphId, group: '' })}
                className="ml-1 rounded-full border border-zenith-edge bg-black/20 px-2 py-0.5 font-mono text-[9px] uppercase tracking-[0.18em] text-zenith-soft hover:border-white/25 hover:text-white"
              >
                filter
              </button>
            </ProvenanceRow>
          )}
          {sourceArtifact && (
            <ProvenanceRow label="Source artifact">
              <InspectorFileChip path={sourceArtifact} onOpen={onOpenFile} />
            </ProvenanceRow>
          )}
          {sourceBinId && (
            <ProvenanceRow label="Source bin">
              <span className="font-mono text-[11px] text-white/85">{sourceBinId}</span>
            </ProvenanceRow>
          )}
          {relevantFiles.length > 0 && (
            <ProvenanceRow label="Relevant files">
              <div className="flex flex-wrap gap-1">
                {relevantFiles.map((path) => (
                  <InspectorFileChip
                    key={path}
                    path={path}
                    onOpen={onOpenFile}
                  />
                ))}
              </div>
            </ProvenanceRow>
          )}
          {detail.file_refs.length > 0 && (
            <ProvenanceRow label="Neighborhood files">
              <div className="flex flex-wrap gap-1">
                {detail.file_refs.slice(0, 6).map((ref) => (
                  <InspectorFileChip
                    key={ref.value}
                    path={ref.value}
                    onOpen={onOpenFile}
                    count={ref.count}
                  />
                ))}
              </div>
            </ProvenanceRow>
          )}
          {detail.raw_seed_anchor && (
            <ProvenanceRow label="Raw-seed anchor">
              <AuthorityChip
                kind={
                  asString(detail.raw_seed_anchor.id).startsWith('par_')
                    ? 'raw_seed_paragraph'
                    : 'raw_seed_section'
                }
                target={asString(detail.raw_seed_anchor.id)}
                label={asString(detail.raw_seed_anchor.id)}
                onClick={() =>
                  onOpenDrill({
                    kind: asString(detail.raw_seed_anchor?.id ?? '').startsWith('par_')
                      ? 'raw_seed_paragraph'
                      : 'raw_seed_section',
                    target: asString(detail.raw_seed_anchor?.id ?? ''),
                  })
                }
                compact
              />
            </ProvenanceRow>
          )}
        </dl>
      </section>

      {/* Neighborhood + siblings */}
      <section className="rounded-[var(--zenith-radius-lg)] border border-zenith-edge bg-black/25 px-3 py-[var(--zenith-space-2-5)]">
        <div className="panel-kicker">Neighborhood</div>
        {(before.length > 0 || after.length > 0) ? (
          <div className="mt-2 grid gap-1.5">
            <NeighborRow label="Before" shards={before} onSelect={onSelectShard} />
            <NeighborRow label="After" shards={after} onSelect={onSelectShard} />
          </div>
        ) : (
          <p className="mt-1 text-[11px] text-[var(--zenith-soft)]">
            No ordered neighbors for this shard.
          </p>
        )}
        {detail.paragraph_siblings.length > 0 && (
          <div className="mt-2.5">
            <div className="panel-kicker">
              Paragraph siblings · {detail.paragraph_siblings.length}
            </div>
            <div className="mt-1 flex flex-wrap gap-1">
              {detail.paragraph_siblings.slice(0, 8).map((sibling) => (
                <AuthorityChip
                  key={asString(sibling.id)}
                  kind="shard"
                  target={asString(sibling.id)}
                  label={asString(sibling.id)}
                  onClick={() => onSelectShard(asString(sibling.id))}
                  compact
                />
              ))}
            </div>
          </div>
        )}
        {detail.group_siblings.length > 0 && (
          <div className="mt-2.5">
            <div className="panel-kicker">
              Group siblings · {detail.group_siblings.length} group(s)
            </div>
            <ul className="mt-1 space-y-1">
              {detail.group_siblings.slice(0, 3).map((bucket) => (
                <li
                  key={bucket.group_id}
                  className="rounded-[var(--zenith-radius-sm)] border border-zenith-edge bg-white/[0.02] px-2 py-1.5"
                >
                  <div className="flex items-center justify-between gap-2">
                    <button
                      type="button"
                      onClick={() => onFilter({ group: bucket.group_id, paragraph: '' })}
                      className="inline-flex items-center gap-1 rounded-full border border-zenith-edge bg-black/20 px-2 py-0.5 font-mono text-[10px] uppercase tracking-[0.18em] text-zenith-soft hover:border-white/25 hover:text-white"
                      title="Filter by this group"
                    >
                      <Hash size={9} />
                      {bucket.group_id}
                    </button>
                    <span className="font-mono text-[10px] text-white/45">
                      {bucket.siblings.length}
                    </span>
                  </div>
                  <div className="mt-1 flex flex-wrap gap-1">
                    {bucket.siblings.slice(0, 6).map((sibling) => (
                      <AuthorityChip
                        key={asString(sibling.id)}
                        kind="shard"
                        target={asString(sibling.id)}
                        label={asString(sibling.id)}
                        onClick={() => onSelectShard(asString(sibling.id))}
                        compact
                      />
                    ))}
                  </div>
                </li>
              ))}
            </ul>
          </div>
        )}
      </section>

      {/* Authority chain */}
      <section className="rounded-[var(--zenith-radius-lg)] border border-zenith-edge bg-black/25 px-3 py-[var(--zenith-space-2-5)]">
        <div className="panel-kicker mb-2">Authority chain</div>
        <AuthorityChainView handle={{ kind: 'shard', id: detail.shard_id }} />
      </section>
    </div>
  );
}


function ProvenanceRow({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="grid grid-cols-[120px_1fr] items-start gap-2">
      <dt className="panel-kicker">{label}</dt>
      <dd className="flex min-w-0 flex-wrap items-center gap-1">{children}</dd>
    </div>
  );
}

function InspectorFileChip({
  path,
  onOpen,
  count,
}: {
  path: string;
  onOpen: (path: string) => void;
  count?: number;
}) {
  return (
    <button
      type="button"
      onClick={() => onOpen(path)}
      className="inline-flex max-w-full items-center gap-1 rounded-full border border-zenith-edge bg-white/[0.04] px-2 py-0.5 font-mono text-[10px] text-white/80 transition-colors hover:border-white/25 hover:bg-white/[0.08] hover:text-white"
      title={`Open ${path} in Inspector`}
      aria-label={`Open ${path} in Inspector`}
    >
      <FileCode2 size={10} className="shrink-0 opacity-60" />
      <span className="truncate">{fileLabel(path)}</span>
      {typeof count === 'number' && <span className="text-zenith-muted">· {count}</span>}
      <ArrowUpRight size={10} className="shrink-0 opacity-55" />
    </button>
  );
}

function NeighborRow({
  label,
  shards,
  onSelect,
}: {
  label: string;
  shards: Array<Record<string, unknown>>;
  onSelect: (shardId: string) => void;
}) {
  if (shards.length === 0) return null;
  return (
    <div className="flex flex-wrap items-center gap-1">
      <span className="panel-kicker">{label}</span>
      {shards.map((shard) => (
        <AuthorityChip
          key={asString(shard.id)}
          kind="shard"
          target={asString(shard.id)}
          label={asString(shard.id)}
          onClick={() => onSelect(asString(shard.id))}
          compact
        />
      ))}
    </div>
  );
}
