import { afterEach, describe, expect, it, vi } from 'vitest';
import { act, cleanup, render, screen, waitFor } from '@testing-library/react';

import WorkLens, {
  __resetWorkLensCacheForTests,
  __workLensLaneForMarkForTests,
} from '../WorkLens';
import { api } from '../../../api';

vi.mock('../../../api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../../../api')>();
  return {
    ...actual,
    api: {
      ...actual.api,
      worldModel: {
        ...actual.api.worldModel,
        workLedgerOverview: vi.fn(),
        taskLedgerProjection: vi.fn(),
        workItemDossier: vi.fn(),
      },
    },
  };
});

vi.mock('../WorkAtlas', () => ({
  default: () => <div data-testid="work-atlas" />,
}));

vi.mock('../NeighborhoodInspector', () => ({
  default: () => <div data-testid="neighborhood-inspector" />,
}));

function workRow(id: string, title: string, actor = 'codex') {
  return {
    id,
    title,
    state: 'execution',
    work_item_type: 'task',
    actor,
    family_id: '09_54_1',
  };
}

afterEach(() => {
  cleanup();
  __resetWorkLensCacheForTests();
  vi.restoreAllMocks();
  vi.useRealTimers();
});

describe('WorkLens', () => {
  it('deduplicates repeated WorkItems before rendering the priority queue', async () => {
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {});
    vi.mocked(api.worldModel.workLedgerOverview).mockResolvedValue({
      schema: 'work_ledger_overview_v1',
      phase_id: '09_54_1',
      family_id: '09_54_1',
      counts: {},
      open_by_actor: {
        codex: [
          workRow('td_duplicate', 'Shared WorkItem', 'codex'),
          workRow('td_unique', 'Unique WorkItem', 'codex'),
        ],
        claude: [
          workRow('td_duplicate', 'Shared WorkItem duplicate', 'claude'),
        ],
      },
      stale_open: [
        workRow('td_duplicate', 'Shared WorkItem stale duplicate', 'codex'),
      ],
      recently_closed: [],
      handoff_candidates: { items: [] },
    } as never);
    vi.mocked(api.worldModel.taskLedgerProjection).mockReturnValue(new Promise(() => {}));
    vi.mocked(api.worldModel.workItemDossier).mockReturnValue(new Promise(() => {}));

    render(<WorkLens />);

    expect(await screen.findByText('2 open')).toBeInTheDocument();
    await waitFor(() => {
      expect(document.querySelectorAll('[data-zenith-work-queue-row-id="td_duplicate"]')).toHaveLength(1);
      expect(document.querySelectorAll('[data-zenith-work-queue-row-id="td_unique"]')).toHaveLength(1);
    });
    const queue = document.querySelector('[data-zenith-work-priority-queue="contained"]');
    const queueList = document.querySelector('[data-zenith-work-priority-queue-list="scroll"]');
    expect(queue?.getAttribute('class')).toContain('max-h-[520px]');
    expect(queueList?.getAttribute('class')).toContain('overflow-y-auto');
    expect(
      consoleError.mock.calls.some((call) =>
        call.some((part) => String(part).includes('Encountered two children with the same key')),
      ),
    ).toBe(false);
  });

  it('times out a cold Work Ledger overview instead of leaving the lens loading forever', async () => {
    vi.useFakeTimers();
    vi.mocked(api.worldModel.workLedgerOverview).mockReturnValue(new Promise(() => {}));
    vi.mocked(api.worldModel.taskLedgerProjection).mockReturnValue(new Promise(() => {}));
    vi.mocked(api.worldModel.workItemDossier).mockReturnValue(new Promise(() => {}));

    render(<WorkLens />);

    expect(document.querySelector('[data-zenith-intelligence-work="loading"]')).toBeInTheDocument();

    await act(async () => {
      await vi.advanceTimersByTimeAsync(12000);
    });

    expect(document.querySelector('[data-zenith-intelligence-work="error"]')).toBeInTheDocument();
    expect(screen.getByText(/Work Ledger overview timed out after 12s\./)).toBeInTheDocument();
    expect(screen.queryByText('loading work ledger overview…')).not.toBeInTheDocument();
  });

  it('renders a backend warming shell without treating the queue as empty', async () => {
    vi.mocked(api.worldModel.workLedgerOverview).mockResolvedValue({
      schema: 'work_ledger_overview_v1',
      phase_id: '09_54_1',
      family_id: '09',
      counts: {},
      open_by_actor: {},
      stale_open: [],
      recently_closed: [],
      handoff_candidates: { items: [] },
      serving: {
        state: 'warming',
        served_from: 'warming_shell',
      },
    } as never);
    vi.mocked(api.worldModel.taskLedgerProjection).mockReturnValue(new Promise(() => {}));
    vi.mocked(api.worldModel.workItemDossier).mockReturnValue(new Promise(() => {}));

    render(<WorkLens />);

    expect(await screen.findByText(/backend warming · Work Ledger overview refresh is in flight/i)).toBeInTheDocument();
    expect(document.querySelector('[data-zenith-intelligence-work="warming"]')).toBeInTheDocument();
    expect(screen.queryByText(/no open Work Ledger threads/i)).not.toBeInTheDocument();
  });

  it('discloses disk last-good Work Ledger data without blocking the queue', async () => {
    vi.mocked(api.worldModel.workLedgerOverview).mockResolvedValue({
      schema: 'work_ledger_overview_v1',
      phase_id: '09_54_1',
      family_id: '09',
      counts: {},
      open_by_actor: {
        codex: [workRow('td_last_good', 'Last-good row', 'codex')],
      },
      stale_open: [],
      recently_closed: [],
      handoff_candidates: { items: [] },
      serving: {
        state: 'stale',
        served_from: 'disk_last_good',
        refresh_in_flight: true,
      },
    } as never);
    vi.mocked(api.worldModel.taskLedgerProjection).mockReturnValue(new Promise(() => {}));
    vi.mocked(api.worldModel.workItemDossier).mockReturnValue(new Promise(() => {}));

    render(<WorkLens />);

    expect((await screen.findAllByText('Last-good row')).length).toBeGreaterThan(0);
    expect(document.querySelector('[data-zenith-intelligence-work="ready"]')).toBeInTheDocument();
    expect(screen.getByText(/serving last-good Work Ledger snapshot · refresh in flight/i)).toBeInTheDocument();
    expect(screen.queryByText(/backend warming · Work Ledger overview refresh is in flight/i)).not.toBeInTheDocument();
  });

  it('discloses backend-capped Work Ledger queue slices', async () => {
    vi.mocked(api.worldModel.workLedgerOverview).mockResolvedValue({
      schema: 'work_ledger_overview_v1',
      phase_id: '09_54_1',
      family_id: '09',
      counts: {},
      open_by_actor: {
        codex: [workRow('td_visible', 'Visible row', 'codex')],
      },
      stale_open: [],
      recently_closed: [],
      handoff_candidates: { items: [] },
      serving: {
        state: 'ready',
        served_from: 'source_projection',
        open_by_actor_total: 42,
        open_by_actor_returned: 25,
        open_by_actor_truncated: true,
      },
    } as never);
    vi.mocked(api.worldModel.taskLedgerProjection).mockReturnValue(new Promise(() => {}));
    vi.mocked(api.worldModel.workItemDossier).mockReturnValue(new Promise(() => {}));

    render(<WorkLens />);

    expect(await screen.findByText('backend slice · 25 of 42 open rows')).toBeInTheDocument();
    expect(document.querySelector('[data-zenith-work-overview-slice-disclosure="true"]')).toBeInTheDocument();
  });

  it('promotes a backend warming shell to ready after a bounded retry', async () => {
    vi.useFakeTimers();
    vi.mocked(api.worldModel.workLedgerOverview)
      .mockResolvedValueOnce({
        schema: 'work_ledger_overview_v1',
        phase_id: '09_54_1',
        family_id: '09',
        counts: {},
        open_by_actor: {},
        stale_open: [],
        recently_closed: [],
        handoff_candidates: { items: [] },
        serving: {
          state: 'warming',
          served_from: 'warming_shell',
        },
      } as never)
      .mockResolvedValueOnce({
        schema: 'work_ledger_overview_v1',
        phase_id: '09_54_1',
        family_id: '09',
        counts: {},
        open_by_actor: {
          codex: [workRow('td_ready', 'Ready after prewarm', 'codex')],
        },
        stale_open: [],
        recently_closed: [],
        handoff_candidates: { items: [] },
        serving: {
          state: 'ready',
          served_from: 'source_projection',
        },
      } as never);
    vi.mocked(api.worldModel.taskLedgerProjection).mockReturnValue(new Promise(() => {}));
    vi.mocked(api.worldModel.workItemDossier).mockReturnValue(new Promise(() => {}));

    render(<WorkLens />);

    await act(async () => {
      await Promise.resolve();
    });

    expect(screen.getByText(/backend warming · Work Ledger overview refresh is in flight/i)).toBeInTheDocument();
    expect(document.querySelector('[data-zenith-intelligence-work="warming"]')).toBeInTheDocument();

    await act(async () => {
      await vi.advanceTimersByTimeAsync(750);
    });
    await act(async () => {
      await Promise.resolve();
    });

    expect(screen.getByText('1 open')).toBeInTheDocument();
    expect(screen.getAllByText('Ready after prewarm').length).toBeGreaterThan(0);
    expect(document.querySelector('[data-zenith-intelligence-work="ready"]')).toBeInTheDocument();
    expect(screen.queryByText(/backend warming · Work Ledger overview refresh is in flight/i)).not.toBeInTheDocument();
    expect(api.worldModel.workLedgerOverview).toHaveBeenCalledTimes(2);
  });

  it('keeps polling disk last-good Work Ledger data while refresh is in flight', async () => {
    vi.useFakeTimers();
    vi.mocked(api.worldModel.workLedgerOverview)
      .mockResolvedValueOnce({
        schema: 'work_ledger_overview_v1',
        phase_id: '09_54_1',
        family_id: '09',
        counts: {},
        open_by_actor: {
          codex: [workRow('td_last_good', 'Last-good row', 'codex')],
        },
        stale_open: [],
        recently_closed: [],
        handoff_candidates: { items: [] },
        serving: {
          state: 'stale',
          served_from: 'disk_last_good',
          refresh_in_flight: true,
        },
      } as never)
      .mockResolvedValueOnce({
        schema: 'work_ledger_overview_v1',
        phase_id: '09_54_1',
        family_id: '09',
        counts: {},
        open_by_actor: {
          codex: [workRow('td_fresh', 'Fresh source row', 'codex')],
        },
        stale_open: [],
        recently_closed: [],
        handoff_candidates: { items: [] },
        serving: {
          state: 'ready',
          served_from: 'source_projection',
        },
      } as never);
    vi.mocked(api.worldModel.taskLedgerProjection).mockResolvedValue({} as never);
    vi.mocked(api.worldModel.workItemDossier).mockResolvedValue({} as never);

    render(<WorkLens />);

    await act(async () => {
      await Promise.resolve();
    });

    expect(screen.getAllByText('Last-good row').length).toBeGreaterThan(0);
    expect(document.querySelector('[data-zenith-intelligence-work="ready"]')).toBeInTheDocument();
    expect(screen.getByText(/serving last-good Work Ledger snapshot · refresh in flight/i)).toBeInTheDocument();

    act(() => {
      vi.advanceTimersByTime(750);
    });
    await act(async () => {
      await Promise.resolve();
    });

    expect(screen.getByText('1 open')).toBeInTheDocument();
    expect(screen.getAllByText('Fresh source row').length).toBeGreaterThan(0);
    expect(screen.queryByText(/serving last-good Work Ledger snapshot/i)).not.toBeInTheDocument();
    expect(api.worldModel.workLedgerOverview).toHaveBeenCalledTimes(2);
  });

  it('keeps the cold-open queue selection local instead of rewriting the URL and remounting', async () => {
    const onSelectedWorkItemChange = vi.fn();
    vi.mocked(api.worldModel.workLedgerOverview).mockResolvedValue({
      schema: 'work_ledger_overview_v1',
      phase_id: '09_54_1',
      family_id: '09_54_1',
      counts: {},
      open_by_actor: {
        codex: [workRow('td_default', 'Default row', 'codex')],
      },
      stale_open: [],
      recently_closed: [],
      handoff_candidates: { items: [] },
    } as never);
    vi.mocked(api.worldModel.taskLedgerProjection).mockResolvedValue({} as never);
    vi.mocked(api.worldModel.workItemDossier).mockResolvedValue({} as never);

    render(<WorkLens onSelectedWorkItemChange={onSelectedWorkItemChange} />);

    expect(await screen.findByText('1 open')).toBeInTheDocument();
    expect(screen.getAllByText('Default row').length).toBeGreaterThan(0);
    expect(onSelectedWorkItemChange).not.toHaveBeenCalled();
  });

  it('reuses the last overview on remount so URL selections do not blank the lens', async () => {
    vi.mocked(api.worldModel.workLedgerOverview).mockResolvedValueOnce({
      schema: 'work_ledger_overview_v1',
      phase_id: '09_54_1',
      family_id: '09_54_1',
      counts: {},
      open_by_actor: {
        codex: [workRow('td_cached', 'Cached row', 'codex')],
      },
      stale_open: [],
      recently_closed: [],
      handoff_candidates: { items: [] },
    } as never);
    vi.mocked(api.worldModel.taskLedgerProjection).mockReturnValue(new Promise(() => {}));
    vi.mocked(api.worldModel.workItemDossier).mockReturnValue(new Promise(() => {}));

    render(<WorkLens />);
    expect(await screen.findByText('1 open')).toBeInTheDocument();
    cleanup();

    vi.mocked(api.worldModel.workLedgerOverview).mockReturnValue(new Promise(() => {}));
    render(<WorkLens selectedWorkItemId="td_cached" objectToken="work_item:td_cached" />);

    expect(document.querySelector('[data-zenith-intelligence-work="ready"]')).toBeInTheDocument();
    expect(screen.getAllByText('Cached row').length).toBeGreaterThan(0);
    expect(screen.queryByText('loading work ledger overview…')).not.toBeInTheDocument();
  });

  it('keeps a ready queue dossier from exposing loading copy when detail is slow', async () => {
    vi.mocked(api.worldModel.workLedgerOverview).mockResolvedValue({
      schema: 'work_ledger_overview_v1',
      phase_id: '09_54_1',
      family_id: '09_54_1',
      counts: {},
      open_by_actor: {
        codex: [workRow('td_default', 'Default row', 'codex')],
      },
      stale_open: [],
      recently_closed: [],
      handoff_candidates: { items: [] },
    } as never);
    vi.mocked(api.worldModel.taskLedgerProjection).mockReturnValue(new Promise(() => {}));
    vi.mocked(api.worldModel.workItemDossier).mockReturnValue(new Promise(() => {}));

    render(<WorkLens />);

    expect((await screen.findAllByText('Default row')).length).toBeGreaterThan(0);
    expect(document.querySelector('[data-zenith-intelligence-work="ready"]')).toBeInTheDocument();
    expect(await screen.findByText('dossier detail pending · td_default')).toBeInTheDocument();
    expect(screen.queryByText(/loading dossier/i)).not.toBeInTheDocument();
  });

  it('classifies queue-visible atlas marks from the backend overlay namespace', () => {
    const mark = {
      id: 'cap_alpha',
      title: 'Alpha cap',
      state: 'execution',
      work_item_type: 'cap',
      overlays: {
        queue_visible: true,
      },
    } as never;

    expect(__workLensLaneForMarkForTests(mark, new Set(['td_alpha']))).toBe('queue_visible');
  });
});
