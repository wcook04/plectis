import { type CandidateRun } from '../api';

const ET_CLOCK = new Intl.DateTimeFormat('en-US', {
  timeZone: 'America/New_York',
  hour: '2-digit',
  minute: '2-digit',
  hour12: false,
});

const MARKET_OPEN_MINUTES = 9 * 60 + 30; // 09:30 ET
const MARKET_CLOSE_MINUTES = 16 * 60; // 16:00 ET

export interface RunAffinityOptions {
  missionName?: string | null;
  stickyRunId?: string | null;
  nowMs?: number;
  closeBias?: number;
  openBias?: number;
  requireWorking?: boolean;
}

export interface RunAffinityRecommendation {
  runId: string;
  score: number;
  shortReason: string;
  detailReason: string;
}

interface RankedCandidate {
  run: CandidateRun;
  score: number;
  ageHours: number;
  closeDistanceMin: number;
  openDistanceMin: number;
  hasCloseContext: boolean;
}

function parseEtClockMinutes(epochSeconds: number): number {
  const parts = ET_CLOCK.formatToParts(new Date(epochSeconds * 1000));
  let hour = 0;
  let minute = 0;
  for (const part of parts) {
    if (part.type === 'hour') hour = Number(part.value);
    if (part.type === 'minute') minute = Number(part.value);
  }
  return (hour * 60) + minute;
}

function circularDistanceMinutes(a: number, b: number): number {
  const diff = Math.abs(a - b);
  return Math.min(diff, 1440 - diff);
}

function boundedWindowScore(distanceMin: number, radiusMin: number, ceiling: number): number {
  if (distanceMin >= radiusMin) return 0;
  const normalized = (radiusMin - distanceMin) / radiusMin;
  return normalized * ceiling;
}

function hasUsCloseContext(run: CandidateRun): boolean {
  const policy = (run.temporal?.horizon_policy ?? '').toLowerCase();
  const label = (run.temporal?.horizon_label ?? '').toLowerCase();
  return policy.includes('next_us_close') || policy.includes('us_close') || label.includes('us close') || label.includes('close');
}

function formatMinutes(value: number): string {
  const rounded = Math.max(1, Math.round(value));
  return `${rounded}m`;
}

function scoreCandidate(run: CandidateRun, options: RunAffinityOptions, nowSec: number): RankedCandidate {
  const ageHours = Math.max(0, (nowSec - run.timestamp) / 3600);
  const etMinutes = parseEtClockMinutes(run.timestamp);
  const closeDistanceMin = circularDistanceMinutes(etMinutes, MARKET_CLOSE_MINUTES);
  const openDistanceMin = circularDistanceMinutes(etMinutes, MARKET_OPEN_MINUTES);
  const closeBias = options.closeBias ?? 1.35;
  const openBias = options.openBias ?? 0.9;
  const closeContext = hasUsCloseContext(run);

  let score = 0;

  score += run.status === 'green' ? 130 : run.status === 'amber' ? 28 : -90;
  if (options.requireWorking && run.status !== 'green') score -= 32;

  score += Math.max(0, 92 - (ageHours * 4.2));
  if (ageHours <= 6) score += 10;
  else if (ageHours <= 24) score += 4;

  if (options.missionName && run.mission_name === options.missionName) score += 14;
  if (run.id === options.stickyRunId) score += 20;

  score += Math.min(10, run.feed_count * 0.8);
  score += boundedWindowScore(closeDistanceMin, 120, 58) * closeBias;
  score += boundedWindowScore(openDistanceMin, 95, 34) * openBias;
  if (closeContext) score += 16;

  return {
    run,
    score,
    ageHours,
    closeDistanceMin,
    openDistanceMin,
    hasCloseContext: closeContext,
  };
}

export function recommendRunByAffinity(
  candidates: CandidateRun[],
  options: RunAffinityOptions = {},
): RunAffinityRecommendation | null {
  if (!candidates.length) return null;
  const nowSec = (options.nowMs ?? Date.now()) / 1000;
  const ranked = candidates
    .map((run) => scoreCandidate(run, options, nowSec))
    .sort((a, b) => {
      if (b.score !== a.score) return b.score - a.score;
      return b.run.timestamp - a.run.timestamp;
    });

  const best = ranked[0];
  if (!best) return null;

  const reasons: string[] = [];
  if (best.run.status === 'green') reasons.push('last working');
  if (best.closeDistanceMin <= 75) {
    reasons.push(`near US close (${formatMinutes(best.closeDistanceMin)})`);
  } else if (best.openDistanceMin <= 60) {
    reasons.push(`near US open (${formatMinutes(best.openDistanceMin)})`);
  }
  if (best.hasCloseContext) reasons.push('US close horizon');
  if (best.run.id === options.stickyRunId) reasons.push('sticky');
  if (best.ageHours <= 8) reasons.push('recent');
  if (reasons.length === 0) reasons.push('best recency fit');

  return {
    runId: best.run.id,
    score: Math.round(best.score),
    shortReason: reasons[0],
    detailReason: reasons.slice(0, 3).join(' • '),
  };
}
