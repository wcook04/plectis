import { afterEach, describe, expect, it, vi } from 'vitest';

import { api, type StationLauncherSnapshot } from '../../api';
import {
  clearStationLauncherWarmingRetry,
  isStationLauncherWarming,
  STATION_LAUNCHER_WARMING_RETRY_MS,
  useStation,
} from '../useStation';

const stationBaseline = useStation.getState();

function warmingLauncherPayload(): StationLauncherSnapshot {
  return {
    schema: 'station_launcher_v1',
    generated_at: '2026-04-17T10:00:00+00:00',
    alerts: [
      {
        id: 'station_launcher:warming',
        tone: 'info',
        label: 'Station launcher warming',
        detail: 'station launcher miss; background refresh is in flight',
      },
    ],
    operations: [],
    diagnostics: {
      cache: { status: 'warming', reason: 'miss' },
      notes: ['Served a schema-clean warming launcher payload.'],
    },
  } as StationLauncherSnapshot;
}

function readyLauncherPayload(): StationLauncherSnapshot {
  return {
    schema: 'station_launcher_v1',
    generated_at: '2026-04-17T10:00:02+00:00',
    family: {
      family_id: '09',
      family_number: '09',
      title: 'Live Family',
    },
    alerts: [],
    operations: [],
    diagnostics: {
      cache: { status: 'ready' },
    },
  } as StationLauncherSnapshot;
}

afterEach(() => {
  clearStationLauncherWarmingRetry();
  useStation.setState(stationBaseline, true);
  vi.useRealTimers();
  vi.restoreAllMocks();
});

describe('useStation launcher warming', () => {
  it('detects backend warming diagnostics as a transitional cache state', () => {
    expect(isStationLauncherWarming(warmingLauncherPayload())).toBe(true);
    expect(isStationLauncherWarming(readyLauncherPayload())).toBe(false);
  });

  it('schedules a forced follow-up refresh after a warming launcher payload', async () => {
    vi.useFakeTimers();
    const ready = readyLauncherPayload();
    const launcherSpy = vi
      .spyOn(api.station, 'launcher')
      .mockResolvedValueOnce(warmingLauncherPayload())
      .mockResolvedValueOnce(ready);

    const firstSnapshot = await useStation.getState().refreshLauncher({ force: true });

    expect(firstSnapshot?.alerts[0]?.id).toBe('station_launcher:warming');
    expect(useStation.getState().launcherWarming).toBe(true);
    expect(useStation.getState().launcherWarmingReason).toBe('miss');
    expect(useStation.getState().launcherLoadedAt).toBeNull();

    await vi.advanceTimersByTimeAsync(STATION_LAUNCHER_WARMING_RETRY_MS);
    await Promise.resolve();
    await Promise.resolve();

    expect(launcherSpy).toHaveBeenCalledTimes(2);
    expect(useStation.getState().launcher).toBe(ready);
    expect(useStation.getState().launcherWarming).toBe(false);
    expect(useStation.getState().launcherLoadedAt).not.toBeNull();
  });
});
