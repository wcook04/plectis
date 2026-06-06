import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { api, type StationLauncherSnapshot } from '../../api';
import { useStation } from '../useStation';

const baseline = useStation.getState();

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
}

function minimalLauncherSnapshot(): StationLauncherSnapshot {
  return {
    schema: 'station_launcher_v1',
    generated_at: '2026-04-17T10:00:00.000Z',
    family: {},
    active_phase: {},
    current_driver: {},
    next_handoff: {},
    orchestration: {},
    missions: {},
    bridge: {},
    observe_runtime: {},
    raw_seed_pipeline: {},
    overnight_chain: {},
    meta_missions: {},
    run: {},
    alerts: [],
    operations: [],
  } as StationLauncherSnapshot;
}

describe('useStation live updates', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2026-04-17T10:00:00.000Z'));
  });

  afterEach(() => {
    useStation.setState(baseline, true);
    vi.restoreAllMocks();
    vi.useRealTimers();
  });

  it('transitions paused, catching_up, live, and stale correctly', () => {
    const store = useStation.getState();

    expect(store.liveUpdates.status).toBe('stale');

    store.setLiveUpdatesPaused(true);
    expect(useStation.getState().liveUpdates.status).toBe('paused');

    store.setLiveUpdatesPaused(false);
    expect(useStation.getState().liveUpdates.status).toBe('stale');

    store.markLiveUpdateSignal('poll');
    store.beginLiveUpdate('poll');
    expect(useStation.getState().liveUpdates.status).toBe('catching_up');
    expect(useStation.getState().liveUpdates.source).toBe('poll');

    store.completeLiveUpdate(true);
    expect(useStation.getState().liveUpdates.status).toBe('live');

    vi.advanceTimersByTime(16_000);
    expect(useStation.getState().refreshLiveUpdateStatus()).toBe('stale');
    expect(useStation.getState().liveUpdates.status).toBe('stale');
  });

  it('allows manual refresh while paused and settles back to paused', () => {
    const store = useStation.getState();

    store.setLiveUpdatesPaused(true);
    expect(useStation.getState().liveUpdates.status).toBe('paused');

    store.beginLiveUpdate('manual');
    expect(useStation.getState().liveUpdates.status).toBe('catching_up');
    expect(useStation.getState().liveUpdates.source).toBe('manual');

    store.completeLiveUpdate(true);
    expect(useStation.getState().liveUpdates.status).toBe('paused');
    expect(useStation.getState().liveUpdates.lastSuccessfulRefreshAt).not.toBeNull();
  });

  it('tracks observe signals through catching_up to live', () => {
    const store = useStation.getState();

    store.markLiveUpdateSignal('observe');
    expect(useStation.getState().liveUpdates.lastSignalAt).not.toBeNull();
    expect(useStation.getState().liveUpdates.source).toBe('observe');

    store.beginLiveUpdate('observe');
    expect(useStation.getState().liveUpdates.status).toBe('catching_up');

    store.completeLiveUpdate(true);
    expect(useStation.getState().liveUpdates.status).toBe('live');
    expect(useStation.getState().liveUpdates.source).toBe('observe');
  });

  it('does not stampede launcher requests while a forced refresh is in flight', async () => {
    const pending = deferred<StationLauncherSnapshot>();
    const launcher = minimalLauncherSnapshot();
    vi.spyOn(api.station, 'launcher').mockReturnValue(pending.promise);

    const first = useStation.getState().refreshLauncher({ force: true });
    expect(useStation.getState().launcherLoading).toBe(true);

    const second = useStation.getState().refreshLauncher({ force: true });
    await expect(second).resolves.toBeNull();
    expect(api.station.launcher).toHaveBeenCalledTimes(1);

    pending.resolve(launcher);
    await expect(first).resolves.toBe(launcher);
    expect(useStation.getState().launcher).toBe(launcher);
  });
});
