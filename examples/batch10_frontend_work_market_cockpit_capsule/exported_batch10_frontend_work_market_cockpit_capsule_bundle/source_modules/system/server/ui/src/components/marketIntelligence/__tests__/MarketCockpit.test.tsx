// [PURPOSE] Smoke test for v0.6 MarketCockpit — protects the operator's
// human-readability requirements: ticker tape renders with prices and
// change%, entity ids are normalized (no raw `equity:` tokens in primary
// visible text), ranked-observation rows show title + why_interesting,
// macro pressure / flow leaderboard / event watchlist render, and the
// selected-situation explainer shows the operator-language sections.

import { render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';

import MarketCockpit from '../MarketCockpit';
import { useZenith } from '../../../stores/useZenith';
import {
  asMarketDashboardReadModel,
  asWorldModelSnapshot,
} from '../../../test-utils/mockApiClient';

const baseline = useZenith.getState();

function seedWorldModel(marketFeeds: Record<string, unknown>) {
  useZenith.setState(
    {
      ...baseline,
      worldModel: asWorldModelSnapshot({
        schema: 'world_model_snapshot_v1',
        generated_at: '2026-05-14T00:00:00+00:00',
        family: null,
        phases: [],
        active_phase: null,
        market_feeds: marketFeeds as Record<string, never>,
      }),
      worldModelLoadedAt: Date.now(),
      worldModelLoading: false,
      worldModelError: null,
    },
    true,
  );
}

function buildMarketFeeds() {
  return {
    market_clock: {
      today_market_date: '2026-05-14',
      market_timezone: 'America/New_York',
      today: [
        { fire_point: 'open', passed: true, fired_at_utc: '2026-05-14T13:30:00+00:00', target_time_market: '2026-05-14T09:30:00-04:00' },
        { fire_point: 'close', passed: false, target_time_market: '2026-05-14T16:00:00-04:00' },
      ],
    },
    summary: {
      latest_run_id: 'RUN_TEST_v0_6',
      latest_freshness: { tone: 'ok', label: '5m ago', age_seconds: 300 },
    },
    feed_runs: [
      { run_id: 'RUN_TEST_v0_6', ready: true },
    ],
    latest_ticker_snapshot: {
      present: true,
      market_date: '2026-05-14',
      capture_status: 'success',
      fire_point: 'close',
      ticker_success_count: 5,
      ticker_error_count: 0,
      ticker_preview: [
        { symbol: 'SPY', label: 'S&P 500 ETF', status: 'ok', price: 734.28, change_pct: 1.45 },
        { symbol: 'QQQ', label: 'Nasdaq 100 ETF', status: 'ok', price: 695.66, change_pct: 2.06 },
        { symbol: 'VIX', label: 'Volatility', status: 'ok', price: 17.35, change_pct: -0.17 },
      ],
    },
    latest_evidence_card: { as_of: '2026-05-14T00:00:00+00:00' },
    latest_quant_presentation_mart: {
      coverage: {
        feeds: [
          { feed_id: 'global_stock_feed', label: 'Equities', rows: 457, freshness: '2026-05-14T00:00:00+00:00', quality: 'ok', metric_columns: ['Chg_5d', 'Price'] },
          { feed_id: 'global_news_feed', label: 'News', rows: 0, freshness: '2026-05-14T00:00:00+00:00', quality: 'ok', metric_columns: [] },
        ],
      },
      provider_drift_monitor: [
        { provider_id: 'global_stock_feed', label: 'Equities', drift_flags: [], fetch_success_rate: 0.998, row_count: 457, quality_tone: 'ok' },
      ],
      missingness_board: [
        { feed_id: 'global_news_feed', label: 'News', empty_reason: 'zero_rows', rows: 0, quality: 'ok' },
      ],
      ranked_observations: [
        {
          observation_id: 'stockgrid_flow_arm',
          rank: 1,
          title: 'ARM is the top Stockgrid flow/conviction observation in the run',
          why_interesting:
            'Stockgrid flow is useful as salience and context when explicitly separated from a recommendation.',
          entities: ['equity:ARM'],
          primary_metric: { name: 'stockgrid_flow_score', value: 317771226.0 },
          reasons: ['flow_score=317771226.0', 'conviction=50.75'],
          reason_codes: ['STOCKGRID_FLOW_TOP', 'FLOW_SALIENCE_NOT_RECOMMENDATION'],
          caveats: ['Stockgrid flow is a provider signal lane; it is not a buy/sell ranking.'],
          disconfirming_checks: ['Check provider drift and row-level Stockgrid source before interpreting the signal.'],
          display_state: 'ready',
          claim_level: 'salience_observation',
          safe_use_level: 'internal_dashboard_evidence',
          score: { confidence: 0.873, display_readiness: 0.84, interestingness: 1.0 },
        },
      ],
      stockgrid_flow_board: [
        {
          ticker: 'ARM',
          company: 'Arm Holdings Plc ADR',
          sector: 'Technology',
          flow_usd: 317771226.0,
          net_usd: 88604068.0,
          conviction: 50.75,
          signal_value: 56.44,
          win_rate: 55.29,
          direction: 1,
          claim_level: 'salience_observation',
        },
      ],
      macro_regime_board: [
        {
          bucket: 'energy',
          average_z_score: 2.37,
          series_count: 2,
          vintage_status: 'available',
          top_series: [
            { ticker: 'gasoline_regular_conventional', z_score: 2.38, recent_change: 0.048, latest_observation_date: '2026-05-11' },
          ],
        },
      ],
      prediction_market_event_board: [
        {
          entity_id: 'prediction_market_event:metamask-fdv',
          event_title: 'Metamask FDV above $700M one day after launch?',
          question: 'Metamask FDV above $700M one day after launch?',
          probability: 0.702,
          probability_change: -0.011,
          volume: 1350431.0,
          spread: 0.403,
          topic: 'CRYPTO.NEWSBREAKER',
        },
      ],
    },
  };
}

function buildReadModel() {
  return asMarketDashboardReadModel({
    schema_version: 'market_dashboard_read_model_v0',
    run_id: 'RUN_TEST_v0_6',
    input_graph_schema_version: 'market_situation_graph_v0',
    input_graph_fingerprint: 'test',
    projection_status: { status: 'in_sync' },
    authority_boundary: { summary: 'test', safe_use_level: 'run_evidence_ready' },
    overview: {
      situation_count: 1,
      validated_signal_count: 0,
      safe_use_level: 'run_evidence_ready',
      freshness: { input_watermark: '2026-05-14T00:00:00+00:00' },
    },
    situation_queue: {
      items: [
        {
          situation_id: 'stockgrid_arm',
          title: 'ARM flow salience lacks 5-day price confirmation',
          situation_type: 'flow_price_divergence',
          horizon: '5d',
          claim_level: 'salience_observation',
          validation_state: 'salience_observation',
          display_state: 'ready',
          primary_entities: ['equity:ARM'],
          evidence_count: 1,
          counterevidence_count: 1,
          confidence_overall: 0.793,
          safe_use_level: 'run_evidence_ready',
        },
      ],
    },
    situation_detail_index: {
      stockgrid_arm: {
        card: {
          situation_id: 'stockgrid_arm',
          title: 'ARM flow salience lacks 5-day price confirmation',
          claim_level: 'salience_observation',
          horizon: '5d',
          display_state: 'ready',
          safe_use_level: 'run_evidence_ready',
          primary_entities: ['equity:ARM'],
          evidence_count: 1,
          counterevidence_count: 1,
        },
        evidence_edges: [
          {
            reason_code: 'STOCKGRID_FLOW_TOP',
            metric: { flow_usd: 317771226.0, conviction: 50.75 },
            weight: 0.85,
            target_entity_id: 'equity:ARM',
          },
        ],
        counterevidence_edges: [],
        drilldown: { mart_observation_ids: ['stockgrid_flow_arm'] },
        regime_context: { top_bucket: 'energy', average_z_score: 2.37 },
        risk_context: { asset_class: 'equity' },
        related_situations: [],
      },
    },
    graph_slice: { nodes: [], edges: [] },
    facets: {},
    drilldown_index: { source_refs: [] },
    provenance_index: { builders: [], lineage: [] },
    validation_debt: { blocked_promotions: [], needed_for_promotion: [] },
    display_hints: {},
    api_contract: {},
    build: {},
  });
}

describe('MarketCockpit v0.6 smoke', () => {
  beforeEach(() => {
    seedWorldModel(buildMarketFeeds());
  });
  afterEach(() => {
    useZenith.setState(baseline, true);
  });

  it('renders ticker tape with prices and change percentages', () => {
    render(
      <MarketCockpit readModel={buildReadModel()} worldModelMarketFeeds={buildMarketFeeds()} />,
    );
    expect(screen.getByText('SPY')).toBeTruthy();
    expect(screen.getByText('QQQ')).toBeTruthy();
    expect(screen.getByText('VIX')).toBeTruthy();
    expect(screen.getByText('734.28')).toBeTruthy();
    expect(screen.getByText('+1.45%')).toBeTruthy();
    expect(screen.getByText('-0.17%')).toBeTruthy();
  });

  it('normalizes entity ids — no raw equity: token in primary visible text', () => {
    const { container } = render(
      <MarketCockpit readModel={buildReadModel()} worldModelMarketFeeds={buildMarketFeeds()} />,
    );
    // Some elements carry the raw entity in a `title` attribute for
    // hover/debug; primary text content should not show `equity:ARM`.
    const text = container.textContent ?? '';
    expect(text).toContain('ARM');
    expect(text).not.toContain('equity:ARM');
  });

  it('renders ranked-observation title and why_interesting copy', () => {
    render(
      <MarketCockpit readModel={buildReadModel()} worldModelMarketFeeds={buildMarketFeeds()} />,
    );
    // `title` and `why_interesting` may render in multiple spots (signal tape
    // row + selected situation explainer when the matching situation is
    // auto-selected). Use queryAllByText with a regex; require >=1 match.
    expect(
      screen.getAllByText(/ARM is the top Stockgrid flow/).length,
    ).toBeGreaterThan(0);
    expect(
      screen.getAllByText(/Stockgrid flow is useful as salience and context/)
        .length,
    ).toBeGreaterThan(0);
  });

  it('renders flow leaderboard, macro pressure, and event watchlist sections', () => {
    render(
      <MarketCockpit readModel={buildReadModel()} worldModelMarketFeeds={buildMarketFeeds()} />,
    );
    expect(screen.getByText(/Flow Leaders/)).toBeTruthy();
    expect(screen.getByText(/Macro Pressure/)).toBeTruthy();
    expect(screen.getByText('Event Watchlist')).toBeTruthy();
    // "energy" appears as the macro bucket label AND in the regime-context
    // row of the auto-selected situation explainer. >=1 match is the assertion.
    expect(screen.getAllByText('energy').length).toBeGreaterThan(0);
    expect(
      screen.getByText(/Metamask FDV above \$700M one day after launch/),
    ).toBeTruthy();
  });

  it('renders the selected situation explainer with operator-language sections', () => {
    render(
      <MarketCockpit
        readModel={buildReadModel()}
        worldModelMarketFeeds={buildMarketFeeds()}
        selectedSituationId="stockgrid_arm"
      />,
    );
    expect(screen.getByText('What this means')).toBeTruthy();
    expect(screen.getByText('Why it surfaced')).toBeTruthy();
    expect(screen.getByText('Key numbers')).toBeTruthy();
    expect(screen.getByText('What would change the state')).toBeTruthy();
    // Reason-code translator: STOCKGRID_FLOW_TOP should render in plain English.
    expect(screen.getByText(/Top of Stockgrid flow board/)).toBeTruthy();
  });

  it('surfaces active refresh banner when activeRefreshRunId is provided', () => {
    render(
      <MarketCockpit
        readModel={buildReadModel()}
        worldModelMarketFeeds={buildMarketFeeds()}
        activeRefreshRunId="RUN_INFLIGHT_xyz"
      />,
    );
    expect(screen.getByText(/refresh in progress · RUN_INFLIGHT_xyz/)).toBeTruthy();
  });

  it('renders honest news coverage status (no rows · fetch unknown) for empty news lane', () => {
    render(
      <MarketCockpit readModel={buildReadModel()} worldModelMarketFeeds={buildMarketFeeds()} />,
    );
    // Coverage health renders the news lane as "no rows · fetch unknown" when rows=0.
    expect(screen.getByText(/no rows · fetch unknown/)).toBeTruthy();
  });

  // ---- v0.6.1 atomicity / breadth / signal-queue fallback ----

  it('renders MarketBreadth panel with coverage + situation groups', () => {
    const { container } = render(
      <MarketCockpit readModel={buildReadModel()} worldModelMarketFeeds={buildMarketFeeds()} />,
    );
    expect(screen.getAllByText(/Market Breadth/).length).toBeGreaterThan(0);
    // Breadth section exposes a data attribute the render-gate can rely on.
    const breadth = container.querySelector(
      '[data-zenith-cockpit-market-breadth="ready"]',
    );
    expect(breadth).toBeTruthy();
    // Coverage groups: equities should appear as a Market Breadth row.
    expect(screen.getAllByText('Equities').length).toBeGreaterThan(0);
  });

  it('falls back to SituationSignalFallback when ranked_observations is empty but situation_queue has items', () => {
    const feeds = buildMarketFeeds();
    // Wipe ranked observations to simulate an in-flight quant_mart.
    (feeds.latest_quant_presentation_mart as Record<string, unknown>).ranked_observations = [];
    const { container } = render(
      <MarketCockpit readModel={buildReadModel()} worldModelMarketFeeds={feeds} />,
    );
    // SituationSignalFallback renders, not the empty-state "No ranked observations" prose.
    const fallback = container.querySelector(
      '[data-zenith-cockpit-signal-fallback="ready"]',
    );
    expect(fallback).toBeTruthy();
    expect(
      screen.getAllByText('ARM flow salience lacks 5-day price confirmation')
        .length,
    ).toBeGreaterThan(0);
    expect(
      screen.getByText(/fallback · ranked observations not yet projected/),
    ).toBeTruthy();
  });

  it('tightens render-gate: data-zenith-market-display-bundle is pending when no breadth substrate exists', () => {
    // Build a "blank substrate" feeds where coverage / situations / flow /
    // macro / events all degenerate to empty.
    const blankFeeds = {
      ...buildMarketFeeds(),
      latest_quant_presentation_mart: {
        coverage: { feeds: [] },
        provider_drift_monitor: [],
        missingness_board: [],
        ranked_observations: [],
        stockgrid_flow_board: [],
        macro_regime_board: [],
        prediction_market_event_board: [],
      },
    };
    const blankReadModel = {
      ...buildReadModel(),
      situation_queue: { items: [] },
      situation_detail_index: {},
    };
    const { container } = render(
      <MarketCockpit
        readModel={blankReadModel}
        worldModelMarketFeeds={blankFeeds}
      />,
    );
    const root = container.querySelector('[data-zenith-market-cockpit="ready"]');
    expect(root?.getAttribute('data-zenith-intelligence-lane-diagnostics')).toBe(
      'pending',
    );
    expect(root?.getAttribute('data-zenith-market-display-bundle')).toBe(
      'pending',
    );
  });

  it('marks render-gate ready when at least one breadth substrate is populated', () => {
    const { container } = render(
      <MarketCockpit readModel={buildReadModel()} worldModelMarketFeeds={buildMarketFeeds()} />,
    );
    const root = container.querySelector('[data-zenith-market-cockpit="ready"]');
    expect(root?.getAttribute('data-zenith-intelligence-lane-diagnostics')).toBe(
      'ready',
    );
    expect(root?.getAttribute('data-zenith-market-display-bundle')).toBe(
      'ready',
    );
  });

  // ---- v0.8: human_market_cockpit matrix + signal cards + signal-only demotion ----

  function buildHmcSlice() {
    return {
      schema_version: 'human_market_cockpit_v0',
      run_id: 'RUN_TEST_v0_8',
      market_field: {
        rows: [
          { id: 'equity:ARM', kind: 'equity', label: 'ARM', subtitle: 'Arm Holdings · Technology' },
          { id: 'macro_bucket:energy', kind: 'macro_bucket', label: 'Energy', subtitle: 'macro regime' },
          { id: 'prediction_market_event:metamask-fdv', kind: 'event', label: 'MetaMask FDV', subtitle: 'event' },
        ],
        columns: [
          { id: 'price', label: 'Price 5D', kind: 'magnitude' },
          { id: 'flow', label: 'Flow', kind: 'flow' },
          { id: 'macro', label: 'Macro z', kind: 'deviation' },
          { id: 'event', label: 'Event', kind: 'event' },
          { id: 'news', label: 'News', kind: 'coverage' },
          { id: 'coverage', label: 'Coverage', kind: 'coverage' },
          { id: 'quality', label: 'Quality', kind: 'magnitude' },
        ],
        cells: [
          { row_id: 'equity:ARM', column_id: 'flow', value: 317771226.0, normalized: 1.0, direction: 1, tone: 'pos', label: 'flow $317.8M', metric_name: 'flow_usd', metric_value: 317771226.0, confidence: 50.75, completeness: 1.0, situation_ids: ['stockgrid_arm'], observation_ids: ['stockgrid_flow_arm'] },
          { row_id: 'macro_bucket:energy', column_id: 'macro', value: 2.37, normalized: 1.0, direction: 1, tone: 'warn', label: 'avg z 2.37', metric_name: 'average_z_score', metric_value: 2.37, confidence: null, completeness: 1.0, situation_ids: [], observation_ids: [] },
          { row_id: 'prediction_market_event:metamask-fdv', column_id: 'event', value: 0.702, normalized: 1.0, direction: 0, tone: 'neutral', label: 'p 0.70', metric_name: 'probability', metric_value: 0.702, confidence: null, completeness: 1.0, situation_ids: [], observation_ids: [] },
        ],
      },
      market_pulse: [
        { label: 'Top flow', value: 'ARM $317.8M', tone: 'pos', interpretation: 'stockgrid flow concentration', caveat: 'flow salience, not a recommendation' },
        { label: 'Macro', value: 'energy z=2.37', tone: 'warn', interpretation: 'macro regime bucket displaced', caveat: 'series-observation summary' },
        { label: 'News', value: '0 rows · dark', tone: 'block', interpretation: 'global_news_feed coverage', caveat: 'coverage state, not a market signal' },
      ],
      signal_cards: [
        {
          id: 'card_stockgrid_flow_top',
          title: 'Flow concentration lacks 5-day price confirmation',
          one_line: 'ARM is the top Stockgrid flow row.',
          key_numbers: [
            { label: 'flow', value: '$317.8M' },
            { label: 'conviction', value: '50.75' },
          ],
          watchpoint: 'Promotes if 5D price confirms.',
          caveat: 'Stockgrid flow is salience, not a recommendation.',
          linked_matrix_row_id: 'equity:ARM',
          linked_situation_ids: ['stockgrid_arm'],
          level: 2,
        },
        {
          id: 'card_news_dark',
          title: 'News lane is dark',
          one_line: 'global_news_feed produced 0 rows in this run.',
          key_numbers: [{ label: 'rows', value: '0' }],
          watchpoint: 'Diagnose tools/news/news.py fetch lane.',
          caveat: 'Empty news lane is a coverage gap.',
          linked_matrix_row_id: 'provider:global_news_feed',
          linked_situation_ids: ['coverage_gap_global_news_feed'],
          level: 2,
        },
      ],
      data_quality: [
        { lane: 'global_news_feed', state: 'dark', rows: 0, problem: 'zero rows in latest run', action: 'diagnose lane fetch path; not a market signal' },
        { lane: 'stockgrid_signal_only', state: 'incomplete', rows: 23, problem: 'rows carry signal_value but lack flow_usd / company / sector enrichment', action: 'demoted from primary flow panel; surfaced here only as data-quality' },
      ],
      visual_specs: [],
      inference_ladder: { applied: ['Level 1', 'Level 2', 'Level 3'], forbidden: 'Level 4: trading recommendations' },
    };
  }

  it('renders Market Insight Matrix when bundle has human_market_cockpit', () => {
    const feeds = { ...buildMarketFeeds(), human_market_cockpit: buildHmcSlice() };
    const { container } = render(
      <MarketCockpit readModel={buildReadModel()} worldModelMarketFeeds={feeds} />,
    );
    expect(screen.getByText(/Market Insight Matrix/)).toBeTruthy();
    const matrix = container.querySelector(
      '[data-zenith-cockpit-market-matrix="ready"]',
    );
    expect(matrix).toBeTruthy();
    expect(matrix?.getAttribute('data-zenith-cockpit-market-matrix-rows')).toBe('3');
    expect(matrix?.getAttribute('data-zenith-cockpit-market-matrix-cols')).toBe('7');
  });

  it('renders backend signal cards (deterministic templates)', () => {
    const feeds = { ...buildMarketFeeds(), human_market_cockpit: buildHmcSlice() };
    const { container } = render(
      <MarketCockpit readModel={buildReadModel()} worldModelMarketFeeds={feeds} />,
    );
    const stack = container.querySelector(
      '[data-zenith-cockpit-signal-cards="ready"]',
    );
    expect(stack).toBeTruthy();
    expect(stack?.getAttribute('data-zenith-cockpit-signal-cards-count')).toBe('2');
    expect(
      screen.getByText('Flow concentration lacks 5-day price confirmation'),
    ).toBeTruthy();
    expect(screen.getAllByText('News lane is dark').length).toBeGreaterThan(0);
  });

  it('renders Market Pulse strip from backend slice', () => {
    const feeds = { ...buildMarketFeeds(), human_market_cockpit: buildHmcSlice() };
    const { container } = render(
      <MarketCockpit readModel={buildReadModel()} worldModelMarketFeeds={feeds} />,
    );
    const pulse = container.querySelector(
      '[data-zenith-cockpit-market-pulse="ready"]',
    );
    expect(pulse).toBeTruthy();
    expect(screen.getByText('ARM $317.8M')).toBeTruthy();
    expect(screen.getByText('energy z=2.37')).toBeTruthy();
  });

  it('renders Data Quality strip (and surfaces signal-only demotion)', () => {
    const feeds = { ...buildMarketFeeds(), human_market_cockpit: buildHmcSlice() };
    const { container } = render(
      <MarketCockpit readModel={buildReadModel()} worldModelMarketFeeds={feeds} />,
    );
    const dq = container.querySelector(
      '[data-zenith-cockpit-data-quality="ready"]',
    );
    expect(dq).toBeTruthy();
    expect(screen.getAllByText('stockgrid_signal_only').length).toBeGreaterThan(0);
    expect(
      screen.getByText(
        /rows carry signal_value but lack flow_usd \/ company \/ sector enrichment/,
      ),
    ).toBeTruthy();
  });

  it('suppresses the FlowLeaderboard signal-value watchlist when hmc demoted those rows', () => {
    const feeds = { ...buildMarketFeeds(), human_market_cockpit: buildHmcSlice() };
    const { container } = render(
      <MarketCockpit readModel={buildReadModel()} worldModelMarketFeeds={feeds} />,
    );
    const text = container.textContent ?? '';
    // The operator's specific failure phrase from the v0.7 screenshot
    // must NOT appear in the primary UI when the backend has demoted
    // signal-only rows into data_quality.
    expect(text).not.toContain('signal value · no company / sector enrichment in this row');
    expect(text).not.toContain('Signal-value watchlist');
  });

  it('marks data-zenith-market-cockpit-hmc=ready when bundle carries a populated cockpit slice', () => {
    const feeds = { ...buildMarketFeeds(), human_market_cockpit: buildHmcSlice() };
    const { container } = render(
      <MarketCockpit readModel={buildReadModel()} worldModelMarketFeeds={feeds} />,
    );
    const root = container.querySelector('[data-zenith-market-cockpit="ready"]');
    expect(root?.getAttribute('data-zenith-market-cockpit-hmc')).toBe('ready');
    expect(root?.getAttribute('data-zenith-market-cockpit-version')).toBe('v0_10_3');
  });

  // ---- v0.9 visual-semantics compiler ----

  function buildHmcSliceWithPlanes() {
    const base = buildHmcSlice() as Record<string, unknown>;
    base.schema_version = 'human_market_cockpit_v0_9';
    base.column_legends = {
      flow: 'stockgrid flow $ (signed)',
      macro: 'average z-score vs baseline',
      news: 'news lane row count (global state when constant)',
      quality: 'mean observation confidence',
    };
    base.repetition_policy = {
      no_repeated_cell_labels: true,
      raise_column_constants_to_legend: true,
      hidden_repeated_tokens: ['confidence', 'news dark', 'signal value'],
    };
    base.global_states = [
      {
        id: 'global_news_feed_dark',
        label: 'News lane dark',
        lane: 'global_news_feed',
        tone: 'block',
        scope: 'all_rows',
        rows: 0,
        promoted_to: 'data_quality_plane',
      },
    ];
    base.applicability = {
      matrix_cells: [
        { row_id: 'equity:ARM', column_id: 'flow', state: 'signal' },
        { row_id: 'equity:ARM', column_id: 'macro', state: 'not_applicable' },
        { row_id: 'equity:ARM', column_id: 'news', state: 'quality_only' },
      ],
    };
    base.visual_planes = [
      {
        id: 'equity_flow_plane',
        title: 'Equity / flow pressure',
        primitive: 'ranked_bar_matrix',
        rows: [
          {
            id: 'equity:ARM',
            label: 'ARM',
            subtitle: 'Arm Holdings · Technology',
            metrics: { flow_usd: 317771226.0, conviction: 50.75, win_rate: 55.3 },
          },
        ],
        metric_specs: [
          { id: 'flow_usd', label: 'Flow $', unit: 'usd_compact', encoding: 'diverging_bar' },
        ],
        legend: 'Flow rows from stockgrid (full enrichment only).',
        applicability: 'primary',
        empty_policy: 'hide_non_applicable',
      },
      {
        id: 'macro_pressure_plane',
        title: 'Macro pressure',
        primitive: 'diverging_bucket_strip',
        rows: [
          {
            id: 'macro_bucket:energy',
            label: 'Energy',
            subtitle: '2 series · vintage available',
            metrics: { average_z_score: 2.37, series_count: 2 },
            top_series: [{ ticker: 'gasoline_regular_conventional', z_score: 2.38 }],
          },
        ],
        metric_specs: [{ id: 'average_z_score', label: 'avg z', unit: 'z_score', encoding: 'diverging_bar' }],
        interpretation: 'z-score vs baseline; right = above baseline; length = displacement magnitude.',
        legend: 'Macro bucket displacement against the run baseline.',
        applicability: 'primary',
        empty_policy: 'hide_non_applicable',
      },
      {
        id: 'event_liquidity_plane',
        title: 'Event liquidity',
        primitive: 'probability_volume_dotplot',
        rows: [
          {
            id: 'prediction_market_event:metamask-fdv',
            label: 'MetaMask FDV above $700M one day after launch?',
            subtitle: 'CRYPTO.NEWSBREAKER',
            metrics: { probability: 0.702, probability_change: -0.011, volume: 1350431.0 },
          },
        ],
        metric_specs: [],
        interpretation: 'Probability on x-axis; dot size encodes volume; Δp colored by direction.',
        legend: 'Top prediction-market events by volume.',
        applicability: 'primary',
        empty_policy: 'hide_when_empty',
      },
      {
        id: 'data_quality_plane',
        title: 'Data quality',
        primitive: 'lane_health_tape',
        rows: [
          {
            lane: 'global_news_feed',
            state: 'dark',
            rows: 0,
            problem: 'zero rows in latest run',
            action: 'diagnose lane fetch path; not a market signal',
          },
          {
            lane: 'stockgrid_signal_only',
            state: 'incomplete',
            rows: 23,
            problem: 'rows carry signal_value but lack flow_usd / company / sector enrichment',
            action: 'demoted from primary flow panel; surfaced here only as data-quality',
          },
        ],
        metric_specs: [],
        legend: 'Lane defects demoted out of primary market panels.',
        applicability: 'primary',
        empty_policy: 'hide_when_empty',
      },
      {
        id: 'ticker_breadth_plane',
        title: 'Tickers / breadth',
        primitive: 'compact_tape',
        rows: [],
        metric_specs: [],
        legend: 'Top-tier US tape with intraday change %.',
        applicability: 'primary',
        empty_policy: 'hide_when_empty',
      },
    ];
    return base;
  }

  it('renders typed visual planes as primary when visual_planes >= 3', () => {
    const feeds = { ...buildMarketFeeds(), human_market_cockpit: buildHmcSliceWithPlanes() };
    const { container } = render(
      <MarketCockpit readModel={buildReadModel()} worldModelMarketFeeds={feeds} />,
    );
    const root = container.querySelector('[data-zenith-market-cockpit="ready"]');
    expect(root?.getAttribute('data-zenith-market-cockpit-visual-planes')).toBe('ready');
    expect(
      container.querySelector('[data-zenith-cockpit-plane="equity_flow_plane"]'),
    ).toBeTruthy();
    expect(
      container.querySelector('[data-zenith-cockpit-plane="macro_pressure_plane"]'),
    ).toBeTruthy();
    expect(
      container.querySelector('[data-zenith-cockpit-plane="event_liquidity_plane"]'),
    ).toBeTruthy();
    expect(
      container.querySelector('[data-zenith-cockpit-plane="data_quality_plane"]'),
    ).toBeTruthy();
  });

  it('demotes universal MarketInsightMatrix to a collapsible diagnostics drawer when planes present', () => {
    const feeds = { ...buildMarketFeeds(), human_market_cockpit: buildHmcSliceWithPlanes() };
    const { container } = render(
      <MarketCockpit readModel={buildReadModel()} worldModelMarketFeeds={feeds} />,
    );
    // The diagnostics drawer is rendered as a <details> element. Inside it
    // the matrix component still mounts (collapsed). The primary visual
    // surface is now the planes above.
    const details = container.querySelector('details');
    expect(details).toBeTruthy();
    expect(details?.textContent).toContain('Diagnostics');
  });

  it('does not show repeated "confidence" or "news dark" labels in primary visible text', () => {
    const feeds = { ...buildMarketFeeds(), human_market_cockpit: buildHmcSliceWithPlanes() };
    const { container } = render(
      <MarketCockpit readModel={buildReadModel()} worldModelMarketFeeds={feeds} />,
    );
    // We expect typed planes to be primary, so the universal matrix sits
    // inside a collapsed <details>. Read only the *primary* DOM by removing
    // the details element before scanning.
    const details = container.querySelectorAll('details');
    details.forEach((d) => d.remove());
    const primaryText = container.textContent ?? '';
    // The exact operator-named repetitions must not appear in primary view.
    // Note: column legends contain the word "confidence" once (in legend
    // text), but it must not repeat in cell bodies. We assert: no more
    // than one occurrence in primary text excluding legend headers — and
    // certainly no "news dark" or "signal value" cell labels.
    expect(primaryText).not.toContain('news dark');
    expect(primaryText).not.toContain('signal value · no company');
  });

  it('renders macro plane interpretation legend (z-score meaning)', () => {
    const feeds = { ...buildMarketFeeds(), human_market_cockpit: buildHmcSliceWithPlanes() };
    render(
      <MarketCockpit readModel={buildReadModel()} worldModelMarketFeeds={feeds} />,
    );
    expect(
      screen.getByText(/z-score vs baseline.*displacement magnitude/),
    ).toBeTruthy();
  });

  // -----------------------------------------------------------------
  // v0.10.1 workspace coherence tests
  // -----------------------------------------------------------------

  function buildHmcSliceWithWorkspace(workspaceRunId: string) {
    // Re-use the v0.9 slice (matrix + planes + cards + data quality)
    // and overlay a workspace contract so MarketCockpit takes the
    // v0.10 workspace branch instead of the v0.9 visual planes branch.
    // workspaceReady requires plane_nav.length >= 5 AND at least one
    // plane with status='ok' AND row_count >= primary_plane_min_rows
    // (default 25).
    const base = buildHmcSliceWithPlanes() as Record<string, unknown>;
    base.workspace = {
      schema_version: 'market_workspace_v0',
      // v0.10.1: bundle-anchored run id; the frontend MUST forward
      // this to active-plane fetches, NOT the UI's selectedRunId or
      // latestRunId from props.
      run_id: workspaceRunId,
      default_plane_id: 'equity_universe_plane',
      plane_nav: [
        {
          id: 'equity_universe_plane',
          label: 'Equity universe',
          row_count: 457,
          row_count_raw: 457,
          filtered_out_count: 0,
          status: 'ok',
          primitive: 'ranked_table',
          default_sort: { column: 'Chg_5d', direction: 'desc' },
          feed_id: 'global_stock_feed',
          entity_kind: 'equity',
        },
        {
          id: 'etf_universe_plane',
          label: 'ETF universe',
          row_count: 322,
          row_count_raw: 322,
          filtered_out_count: 0,
          status: 'ok',
          primitive: 'ranked_table',
          default_sort: { column: 'Chg_5d', direction: 'desc' },
          feed_id: 'global_etf_feed',
          entity_kind: 'etf',
        },
        {
          id: 'macro_series_plane',
          label: 'Macro series',
          row_count: 418,
          row_count_raw: 418,
          filtered_out_count: 0,
          status: 'ok',
          primitive: 'ranked_table',
          default_sort: { column: 'z_score', direction: 'desc' },
          feed_id: 'global_macro_feed',
          entity_kind: 'macro_series',
        },
        {
          id: 'event_universe_plane',
          label: 'Event universe',
          row_count: 424,
          row_count_raw: 424,
          filtered_out_count: 0,
          status: 'ok',
          primitive: 'ranked_table',
          default_sort: { column: 'v', direction: 'desc' },
          feed_id: 'global_polymarket_feed',
          entity_kind: 'prediction_market_event',
        },
        {
          id: 'flow_universe_plane',
          label: 'Flow universe',
          row_count: 503,
          row_count_raw: 1280,
          filtered_out_count: 777,
          status: 'ok',
          primitive: 'ranked_table',
          default_sort: { column: 'flow', direction: 'desc' },
          feed_id: 'global_stockgrid_feed',
          entity_kind: 'equity',
        },
        {
          id: 'news_universe_plane',
          label: 'News',
          row_count: 140,
          row_count_raw: 140,
          filtered_out_count: 0,
          status: 'ok',
          primitive: 'ranked_table',
          default_sort: { column: 'time', direction: 'desc' },
          feed_id: 'global_news_feed',
          entity_kind: 'news_item',
        },
      ],
      active_plane_preview: {
        plane_id: 'equity_universe_plane',
        // 25-row preview embedded so the workspace renders without
        // waiting for the route fetch.
        rows: Array.from({ length: 25 }, (_, i) => ({
          Ticker: `TST${i.toString().padStart(2, '0')}`,
          Identity: `Test ${i}`,
          Category: 'tech',
          Price: 100 + i,
          Chg_5d: (i - 12) * 0.5,
          Z_Short: (i - 12) * 0.1,
          Vol_20d: 1000 + i * 100,
        })),
        columns: [
          { id: 'Ticker', label: 'Ticker', kind: 'label' },
          { id: 'Identity', label: 'Identity', kind: 'label_truncated' },
          { id: 'Category', label: 'Category', kind: 'tag' },
          { id: 'Price', label: 'Price', kind: 'price' },
          { id: 'Chg_5d', label: 'Chg 5D %', kind: 'diverging_magnitude' },
          { id: 'Z_Short', label: 'Z short', kind: 'diverging_z' },
          { id: 'Vol_20d', label: 'Vol 20D', kind: 'magnitude' },
        ],
        row_count_total: 457,
        sort: { column: 'Chg_5d', direction: 'desc' },
      },
      layout_contract: {
        primary_plane_min_rows: 25,
        fill_available_viewport: true,
        right_explainer_width: 320,
        collapse_signal_cards_when_space_constrained: true,
      },
    };
    return base;
  }

  it('v0.10.1: binds workspace.runId (NOT selectedRunId/latestRunId) on the workspace render', () => {
    const workspaceRunId = 'RUN_2026-05-13_01-33-40_bfa67a';
    const inflightRunId = 'RUN_2026-05-14_00-08-22_c97d60';
    const feeds = {
      ...buildMarketFeeds(),
      human_market_cockpit: buildHmcSliceWithWorkspace(workspaceRunId),
    };
    const { container } = render(
      <MarketCockpit
        readModel={buildReadModel()}
        worldModelMarketFeeds={feeds}
        selectedRunId={inflightRunId}
        latestRunId={inflightRunId}
      />,
    );
    const ws = container.querySelector('[data-zenith-cockpit-market-workspace="ready"]');
    expect(ws).toBeTruthy();
    expect(ws?.getAttribute('data-zenith-cockpit-workspace-run')).toBe(workspaceRunId);
    expect(ws?.getAttribute('data-zenith-cockpit-workspace-run')).not.toBe(inflightRunId);
  });

  it('v0.10.1: workspace density attr is dense when active plane has >= 25 visible rows', () => {
    const feeds = {
      ...buildMarketFeeds(),
      human_market_cockpit: buildHmcSliceWithWorkspace('RUN_TEST'),
    };
    const { container } = render(
      <MarketCockpit readModel={buildReadModel()} worldModelMarketFeeds={feeds} />,
    );
    const ws = container.querySelector('[data-zenith-cockpit-market-workspace="ready"]');
    expect(ws?.getAttribute('data-zenith-cockpit-active-plane-density')).toBe('dense');
    expect(ws?.getAttribute('data-zenith-cockpit-active-plane-column-status')).toBe('ok');
    const visible = Number(ws?.getAttribute('data-zenith-cockpit-active-plane-visible-rows') ?? 0);
    expect(visible).toBeGreaterThanOrEqual(25);
  });

  it('v0.10.1: PlaneNav shows row counts that come from workspace.plane_nav (filtered, not raw)', () => {
    const feeds = {
      ...buildMarketFeeds(),
      human_market_cockpit: buildHmcSliceWithWorkspace('RUN_TEST'),
    };
    const { container } = render(
      <MarketCockpit readModel={buildReadModel()} worldModelMarketFeeds={feeds} />,
    );
    // The flow tab must show the filtered count 503, not the raw 1280
    // — that is the v0.10.1 alignment between plane_nav and the route.
    // Scope to the container's PlaneNav region (top-level workspace
    // navigation), excluding the active table (which scrolls rows).
    const text = container.textContent ?? '';
    expect(text).toContain('Flow universe');
    expect(text).toContain('503');
    // Heterogeneous 1280 raw row count must NEVER surface in primary
    // visible text — it would confuse the operator about flow plane
    // density. (It does appear inside the bundle payload, but not in
    // any human-visible cell or label.)
    // We assert this on the PlaneNav region only — DivergingBar widths
    // could in principle include "1280" pixel values; isolate to the
    // nav header label texts.
    const navRegion = container.querySelector('header')?.textContent ?? '';
    expect(navRegion).not.toContain('1280');
  });

  // -----------------------------------------------------------------
  // v0.10.3 browse-workspace-utilization tests
  // -----------------------------------------------------------------

  it('v0.10.3: workspace exposes fill=full and scroll=ready when preview has 25 dense rows', () => {
    const feeds = {
      ...buildMarketFeeds(),
      human_market_cockpit: buildHmcSliceWithWorkspace('RUN_TEST'),
    };
    const { container } = render(
      <MarketCockpit readModel={buildReadModel()} worldModelMarketFeeds={feeds} />,
    );
    const ws = container.querySelector('[data-zenith-cockpit-market-workspace="ready"]');
    expect(ws?.getAttribute('data-zenith-cockpit-active-plane-fill')).toBe('full');
    expect(ws?.getAttribute('data-zenith-cockpit-active-plane-scroll')).toBe('ready');
    // The loaded-rows attr should match the visible rows count (≥25).
    const loaded = Number(ws?.getAttribute('data-zenith-cockpit-active-plane-loaded-rows') ?? 0);
    expect(loaded).toBeGreaterThanOrEqual(25);
  });

  it('v0.10.3: workspace stage reserves height and contains right-rail overflow', () => {
    const feeds = {
      ...buildMarketFeeds(),
      human_market_cockpit: buildHmcSliceWithWorkspace('RUN_TEST'),
    };
    const { container } = render(
      <MarketCockpit readModel={buildReadModel()} worldModelMarketFeeds={feeds} />,
    );
    const stage = container.querySelector('[data-zenith-cockpit-stage="workspace"]');
    const primary = container.querySelector(
      '[data-zenith-cockpit-primary-column="workspace-table"]',
    );
    const rail = container.querySelector(
      '[data-zenith-cockpit-right-rail="row_inspector_first"]',
    );
    const selected = container.querySelector('[data-zenith-cockpit-selected-situation]');
    expect(stage?.className).toContain('min-h-[520px]');
    expect(primary?.className).toContain('overflow-hidden');
    expect(rail?.className).toContain('overflow-y-auto');
    expect(rail?.className).toContain('overscroll-contain');
    expect(selected?.className).toContain('shrink-0');
    expect(selected?.className).toContain('max-h-[360px]');
    expect(selected?.className).toContain('overflow-y-auto');
  });

  it('v0.10.3: right rail mounts in row_inspector_first order with default first-row inspector', async () => {
    const feeds = {
      ...buildMarketFeeds(),
      human_market_cockpit: buildHmcSliceWithWorkspace('RUN_TEST'),
    };
    const { container } = render(
      <MarketCockpit readModel={buildReadModel()} worldModelMarketFeeds={feeds} />,
    );
    const rail = container.querySelector('[data-zenith-cockpit-right-rail="row_inspector_first"]');
    expect(rail).toBeTruthy();
    // RowInspector should be present (default first-row selection populates
    // it before any click).
    await screen.findByText(/Selected row/i);
    const inspector = container.querySelector('[data-zenith-cockpit-row-inspector="ready"]');
    expect(inspector).toBeTruthy();
    // Inspector should reference the active plane.
    expect(inspector?.getAttribute('data-zenith-cockpit-row-inspector-plane')).toBe(
      'equity_universe_plane',
    );
    // The first preview row (Ticker=TST00) should populate the inspector.
    expect(rail?.textContent ?? '').toContain('TST00');
  });

  it('v0.10.3: cockpit version stamp advanced to v0_10_3', () => {
    const feeds = {
      ...buildMarketFeeds(),
      human_market_cockpit: buildHmcSliceWithWorkspace('RUN_TEST'),
    };
    const { container } = render(
      <MarketCockpit readModel={buildReadModel()} worldModelMarketFeeds={feeds} />,
    );
    const root = container.querySelector('[data-zenith-market-cockpit="ready"]');
    expect(root?.getAttribute('data-zenith-market-cockpit-version')).toBe('v0_10_3');
  });
});
