export const LIFECYCLE_COPY_ACK_MS = 15_000;
export const LIFECYCLE_PENDING_COPY_TTL_MS = 25 * 60_000;
export const LIFECYCLE_JUST_FINISHED_MS = 25 * 60_000;
export const LIFECYCLE_RECENT_ACTIVITY_MS = 60_000;
export const LIFECYCLE_LIVE_ACTIVITY_MS = 2 * 60_000;
export const LIFECYCLE_IDLE_THRESHOLD_MS = 25 * 60_000;

export function timestampMs(value) {
  if (value == null || value === '') return null;
  if (typeof value === 'number') {
    if (!Number.isFinite(value)) return null;
    return value > 10_000_000_000 ? Math.floor(value) : Math.floor(value * 1000);
  }
  const parsed = Date.parse(String(value));
  return Number.isFinite(parsed) ? parsed : null;
}

export function titleHasOldRetirePrefix(value) {
  return /^old(?:$|[^a-z0-9])/i.test(String(value || '').trim());
}

function firstText(values) {
  for (const value of values) {
    const text = String(value || '').trim();
    if (text) return text;
  }
  return '';
}

function numberOrNull(value) {
  const n = Number(value);
  return Number.isFinite(n) ? n : null;
}

function shortSessionId(sessionId) {
  const text = String(sessionId || '');
  return text ? text.slice(0, 6) : '';
}

function titleAuthorityIsSource(source) {
  return [
    'codex_thread_name',
    'claude_desktop_title',
    'claude_desktop_user_title',
  ].includes(String(source || ''));
}

export function missionIdentityFacts(row = {}, displayTurn = {}) {
  const titleSource = row.title_source || '';
  const titleText = String(row.title || '').trim();
  const sourceTitle = firstText([
    row.source_title,
    titleAuthorityIsSource(titleSource) ? titleText : '',
  ]);
  const operatorAlias = firstText([
    row.operator_alias,
    titleSource === 'operator_alias' ? titleText : '',
  ]);
  const promptDerivedTitle = firstText([
    row.prompt_derived_title,
    displayTurn.prompt_title,
    row.latest_completed_turn?.prompt_title,
    row.preferred_trace_turn?.prompt_title,
  ]);
  const promptPreview = firstText([
    row.prompt_preview,
    displayTurn.prompt_preview,
    row.preferred_trace_turn?.prompt_preview,
    row.latest_completed_turn?.prompt_preview,
    row.active_turn?.prompt_preview,
  ]);
  const displayTitle = firstText([
    sourceTitle,
    operatorAlias,
    promptDerivedTitle,
    row.display_title,
    row.short_label,
    shortSessionId(row.session_id),
  ]) || 'Untitled mission';
  const sourceTitleVersionMs = numberOrNull(row.source_title_version_ms)
    ?? numberOrNull(row.title_authority_version_ms)
    ?? numberOrNull(row.title_authority?.source_title_version_ms)
    ?? numberOrNull(row.title_authority?.mtime_ms)
    ?? timestampMs(row.title_updated_at);
  const titleMarkerText = firstText([
    sourceTitle,
    operatorAlias,
  ]);
  return {
    displayTitle,
    promptPreview,
    sourceTitle,
    operatorAlias,
    promptDerivedTitle,
    titleSource,
    titleMarker: titleHasOldRetirePrefix(titleMarkerText) ? 'old_prefix' : 'none',
    sourceTitleVersionMs,
  };
}

export function missionDisplayTitle(row = {}, displayTurn = {}) {
  return missionIdentityFacts(row, displayTurn).displayTitle;
}

export function missionPromptPreview(row = {}, displayTurn = {}) {
  return missionIdentityFacts(row, displayTurn).promptPreview;
}

export function retirementFactsForRow(row = {}, identity = missionIdentityFacts(row)) {
  const retirement = row.retirement || {};
  const cause = firstText([
    row.retired_cause,
    retirement.retired_cause,
    row.inactive_reason === 'operator_old_title_marker' || identity.titleMarker === 'old_prefix' ? 'old_prefix' : '',
    row.inactive_reason === 'archived' ? 'archived' : '',
    row.inactive_reason === 'explicit_hidden' ? 'explicit_hidden' : '',
  ]);
  const retiredAtMs = numberOrNull(row.retired_at_ms)
    ?? numberOrNull(retirement.retired_at_ms)
    ?? timestampMs(row.retired_at)
    ?? timestampMs(retirement.retired_at)
    ?? identity.sourceTitleVersionMs
    ?? timestampMs(row.last_activity_at)
    ?? timestampMs(row.mtime_utc);
  const retiredTitleVersionMs = numberOrNull(row.retired_title_version_ms)
    ?? numberOrNull(retirement.retired_title_version_ms)
    ?? identity.sourceTitleVersionMs
    ?? retiredAtMs;
  return {
    retiredCause: cause || 'none',
    retiredAtMs,
    retiredTitleVersionMs,
  };
}

function copyLayer(copyEntry, now, activeNow, lastActivityMs, copyAckMs, pendingCopyTtlMs) {
  if (!copyEntry) return { copy: 'none', copySuccessAtMs: null, copyFailureAtMs: null };
  const startedAt = numberOrNull(copyEntry.startedAt);
  const successAt = numberOrNull(copyEntry.successAt);
  const failureAt = numberOrNull(copyEntry.failureAt);
  const sourceMovedAfterCopy = successAt != null && lastActivityMs != null && lastActivityMs > successAt;
  if (failureAt != null && now - failureAt < copyAckMs) {
    return { copy: 'copy_failed', copySuccessAtMs: successAt, copyFailureAtMs: failureAt };
  }
  if (startedAt != null && successAt == null && failureAt == null) {
    return { copy: 'copying', copySuccessAtMs: null, copyFailureAtMs: null };
  }
  if (successAt != null && !sourceMovedAfterCopy && !activeNow && now - successAt < copyAckMs) {
    return { copy: 'just_copied', copySuccessAtMs: successAt, copyFailureAtMs: null };
  }
  if (successAt != null && !sourceMovedAfterCopy && !activeNow && now - successAt < pendingCopyTtlMs) {
    return { copy: 'pending_after_copy', copySuccessAtMs: successAt, copyFailureAtMs: null };
  }
  return { copy: 'none', copySuccessAtMs: successAt, copyFailureAtMs: failureAt };
}

export function deriveMissionLifecycle(input = {}) {
  const row = input.row || {};
  const now = numberOrNull(input.now) ?? Date.now();
  const copyAckMs = numberOrNull(input.copyAckMs) ?? LIFECYCLE_COPY_ACK_MS;
  const pendingCopyTtlMs = numberOrNull(input.pendingCopyTtlMs) ?? LIFECYCLE_PENDING_COPY_TTL_MS;
  const justFinishedMs = numberOrNull(input.justFinishedMs) ?? LIFECYCLE_JUST_FINISHED_MS;
  const recentActivityMs = numberOrNull(input.recentActivityMs) ?? LIFECYCLE_RECENT_ACTIVITY_MS;
  const liveActivityMs = numberOrNull(input.liveActivityMs) ?? LIFECYCLE_LIVE_ACTIVITY_MS;
  const idleThresholdMs = numberOrNull(input.idleThresholdMs) ?? LIFECYCLE_IDLE_THRESHOLD_MS;
  const displayTurn = input.displayTurn || row.preferred_trace_turn || row.latest_completed_turn || row.active_turn || {};
  const identity = missionIdentityFacts(row, displayTurn);
  const retirement = retirementFactsForRow(row, identity);
  const activeNow = Boolean(input.activeNow);
  const goalStatus = String(row.goal_status || row.goal?.status || '').toLowerCase();
  const goalObserved = String(row.goal_fleet_control?.observed_status || '').toLowerCase();
  const activeGoal = Boolean(input.activeGoal) || goalStatus === 'active' || goalObserved === 'active';
  const staleActive = Boolean(input.staleActive);
  const lastActivityMs = numberOrNull(input.lastActivityMs) ?? timestampMs(row.last_activity_at);
  const completedAtMs = numberOrNull(input.completedAtMs)
    ?? timestampMs(row.latest_completed_turn?.completed_at)
    ?? timestampMs(displayTurn.completed_at);
  const activeStartedAtMs = numberOrNull(input.activeStartedAtMs)
    ?? timestampMs(row.active_turn?.started_at)
    ?? (activeNow ? timestampMs(displayTurn.started_at) : null);
  const transitionedToFinished = Boolean(input.transitionedToFinished);
  const completedRecently = completedAtMs != null && (now - completedAtMs) < justFinishedMs;
  const sinceAct = lastActivityMs != null ? Math.max(0, now - lastActivityMs) : Infinity;
  const activeTurnDormant = !activeGoal && (activeNow || staleActive) && sinceAct >= idleThresholdMs;
  const activeTurnQuiet = !activeGoal && activeNow && !activeTurnDormant && sinceAct >= liveActivityMs;
  const hasTurn = input.hasTurn != null ? Boolean(input.hasTurn) : displayTurn.turn_index != null;
  const rawCopyState = copyLayer(input.copyEntry, now, activeNow || activeGoal, lastActivityMs, copyAckMs, pendingCopyTtlMs);
  const retirementAtMs = retirement.retiredAtMs ?? 0;
  const retirementFreshnessMs = retirement.retiredCause === 'old_prefix'
    ? Math.max(retirementAtMs, retirement.retiredTitleVersionMs ?? 0)
    : retirementAtMs;

  const revivalCandidates = [
    rawCopyState.copySuccessAtMs != null && rawCopyState.copySuccessAtMs >= retirementFreshnessMs ? { at: rawCopyState.copySuccessAtMs, by: 'refresh_copy_capture' } : null,
    activeStartedAtMs != null && activeStartedAtMs >= retirementFreshnessMs ? { at: activeStartedAtMs, by: 'new_activity' } : null,
    completedAtMs != null && completedAtMs >= retirementFreshnessMs ? { at: completedAtMs, by: 'new_activity' } : null,
    lastActivityMs != null && activeNow && lastActivityMs >= retirementFreshnessMs ? { at: lastActivityMs, by: 'new_activity' } : null,
    retirement.retiredCause === 'old_prefix' && identity.titleMarker !== 'old_prefix' ? { at: now, by: 'title_unold' } : null,
  ].filter(Boolean).sort((a, b) => b.at - a.at);
  const revival = revivalCandidates[0] || null;
  const hasRetirementCause = retirement.retiredCause && retirement.retiredCause !== 'none';
  const retirementSuperseded = Boolean(revival && revival.at >= retirementFreshnessMs);
  const retiredCurrent = Boolean(hasRetirementCause && !retirementSuperseded);
  const copyState = retiredCurrent && rawCopyState.copy !== 'copy_failed'
    ? { ...rawCopyState, copy: 'none' }
    : rawCopyState;
  const copyCanOwnPill = !retiredCurrent;

  let activity = 'warm';
  if (copyState.copy === 'copy_failed') activity = retiredCurrent ? 'retired' : 'error';
  else if (retiredCurrent) activity = 'retired';
  else if (activeGoal) activity = 'live';
  else if (staleActive && !activeTurnDormant) activity = 'checking';
  else if (activeTurnQuiet) activity = 'checking';
  else if (activeNow && !activeTurnDormant) activity = 'live';
  else if (copyState.copy === 'just_copied' && copyCanOwnPill) activity = 'copied';
  else if (copyState.copy === 'pending_after_copy' && copyCanOwnPill) activity = 'waiting';
  else if (transitionedToFinished || completedRecently) activity = 'just_finished';
  else if (sinceAct < recentActivityMs) activity = 'recent';
  else if (sinceAct > idleThresholdMs) activity = 'idle';

  let text = 'FINISHED';
  let cls = 'finished';
  let glyph = '✓';
  let reason = 'response finished; copy it to start the waiting-for-response window';
  if (copyState.copy === 'copy_failed') {
    text = 'COPY FAILED'; cls = 'copy_failed'; glyph = '!';
    reason = retiredCurrent ? `copy failed; still retired: ${retirement.retiredCause}` : 'copy failed; see receipt';
  } else if (activity === 'checking') {
    text = 'CHECKING'; cls = 'checking'; glyph = '⋯';
    reason = activeTurnQuiet
      ? 'checking: open turn has no recent trace activity'
      : 'checking: stale cached open turn; refresh will verify final state';
  } else if (activity === 'live') {
    text = 'RUNNING'; cls = 'running'; glyph = '●';
    reason = activeGoal ? 'running: active Codex goal thread' : 'running: fresh active turn';
  } else if (copyState.copy === 'copying') {
    text = 'COPYING'; cls = 'copying'; glyph = '⋯';
    reason = 'copying: writing selected bundle to clipboard';
  } else if (copyState.copy === 'just_copied' && copyCanOwnPill) {
    text = 'COPIED'; cls = 'copied'; glyph = '✓';
    reason = revival?.by === 'refresh_copy_capture' && retirement.retiredCause !== 'none'
      ? 'revived by copy; copied successfully'
      : 'copied successfully';
  } else if (activity === 'just_finished') {
    text = 'FINISHED'; cls = 'finished'; glyph = '✓';
    reason = 'finished: latest response completed';
  } else if ((copyState.copy === 'pending_after_copy' && copyCanOwnPill) || activity === 'waiting') {
    text = 'TYPE B WAIT'; cls = 'waiting'; glyph = '⧖';
    reason = 'waiting_kind=type_b_response_expected: copied, no follow-up yet';
  } else if (activity === 'retired') {
    text = 'RETIRED'; cls = 'retired'; glyph = '×';
    reason = retirement.retiredCause === 'old_prefix'
      ? 'retired: title prefix old'
      : `retired: ${retirement.retiredCause}`;
  } else if (!hasTurn) {
    text = 'NO TURN'; cls = 'partial'; glyph = '';
    reason = 'no trace turn available yet';
  } else if (activity === 'idle') {
    if (activeTurnDormant) {
      text = 'INACTIVE'; cls = 'inactive'; glyph = '·';
      reason = 'inactive: open turn has no source activity for 25 minutes';
    } else {
      text = 'FINISHED'; cls = 'finished'; glyph = '✓';
      reason = 'finished: completed turn is outside the recent queue window';
    }
  } else if (activity === 'recent') {
    text = 'FINISHED'; cls = 'finished'; glyph = '◆';
    reason = 'recent activity; no active response in flight';
  }

  return {
    key: input.key || '',
    activity,
    copy: copyState.copy,
    retired: retiredCurrent,
    identity,
    retirement,
    retirementFreshnessMs,
    revival,
    activeTurnDormant,
    activeTurnQuiet,
    waitingKind: copyState.copy === 'pending_after_copy' || activity === 'waiting' ? 'type_b_response_expected' : 'none',
    pill: { text, cls, title: reason },
    glyph: { glyph, title: reason },
    reason,
  };
}
