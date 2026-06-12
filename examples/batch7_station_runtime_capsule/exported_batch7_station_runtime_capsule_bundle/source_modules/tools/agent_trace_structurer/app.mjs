// v12 boot probe: mark module entry BEFORE any other code that could throw.
// Captured by the WKUserScript installed in Swift; receipt at
// ~/Library/Application Support/Agent Trace Structurer/last_boot_probe.json.
try {
  if (window.__aiwBoot) {
    window.__aiwBoot.script_started = true;
    window.__aiwBoot.script_started_at = new Date().toISOString();
    if (window.__aiwBootPost) window.__aiwBootPost('script_started');
  }
} catch (_) {}

import {
  deriveMissionLifecycle,
  missionDisplayTitle as reducerMissionDisplayTitle,
  missionPromptPreview as reducerMissionPromptPreview,
  titleHasOldRetirePrefix as reducerTitleHasOldRetirePrefix,
} from './lifecycle_reducer.mjs';
import { buildAttachmentClip, classifyClipboardText, defaultTraceFilename, parseAgentTrace } from './parser.mjs';

const els = {
  source: document.querySelector('#source'),
  filename: document.querySelector('#filename'),
  status: document.querySelector('#status'),
  saveTarget: document.querySelector('#save-target'),
  watchState: document.querySelector('#watch-state'),
  captureProfile: document.querySelector('#capture-profile'),
  clipProfile: document.querySelector('#clip-profile'),
  clipboardSignal: document.querySelector('#clipboard-signal'),
  savedList: document.querySelector('#saved-list'),
  latestSummary: document.querySelector('#latest-summary'),
  file: document.querySelector('#file'),
  query: document.querySelector('#query'),
  json: document.querySelector('#json'),
  contract: document.querySelector('#contract'),
  timeline: document.querySelector('#timeline'),
  entities: document.querySelector('#entities'),
  sections: document.querySelector('#sections'),
  stats: document.querySelector('#stats'),
  entityTabs: document.querySelector('#entity-tabs'),
  buttons: {
    toggleWatch: document.querySelector('#toggle-watch'),
    openDownloads: document.querySelector('#open-downloads'),
    paste: document.querySelector('#paste'),
    import: document.querySelector('#import'),
    copy: document.querySelector('#copy'),
    download: document.querySelector('#download'),
    clear: document.querySelector('#clear'),
    clearHistory: document.querySelector('#clear-history'),
    latest: document.querySelector('#latest-file'),
    operatorHud: document.querySelector('#operator-hud'),
    reinstallApp: document.querySelector('#reinstall-app'),
    promptHotkeys: document.querySelector('#prompt-hotkeys'),
    minimizeBar: document.querySelector('#minimize-bar'),
  },
};

// v12 boot fix: hoist activeDropdown declaration to module top so
// applySystemBarMode (called during module init at ~line 1825) doesn't
// hit a temporal-dead-zone ReferenceError. Was originally declared in
// the workbench section ~line 1998; that line is now an assignment.
let activeDropdown = null;
let dropdownEls = null;
let dropdownSearch = '';
let activeEntityGroup = 'paths';
let currentPacket = parseAgentTrace('', els.filename.value);
let currentGeneratedAt = null;
let clipboardWatchEnabled = true;
let nativeState = {};
let savedCaptures = [];
let latestClipboardSnapshot = null;
const pendingNativeDownloads = new Map();
const pendingNativeStores = new Map();
const toolbarDragHandle = document.querySelector('.topbar');
const systemBarSurface = document.querySelector('.app');
let toolbarDrag = null;
let lastToolbarDragEndedAt = 0;
// The native window starts compact. Keep the DOM in the same state so the
// compact frame never renders the expanded workbar clipped inside it.
let systemBarPinned = false;
let systemBarHover = false;
let systemBarExpanded = false;
let systemBarCollapseTimer = 0;
let systemBarRevealTimer = 0;
let systemBarCompactHoverTimer = 0;
let systemBarLastMode = 'compact';
let promptHotkeysEnabled = false;
let promptHotkeysBusy = false;

// Mission Rail state. Read from Swift bridge requestMissionIndex; the JS never
// scans ~/.claude or ~/.codex on render. Selection is per provider:session_id.
let missionIndex = null;
let lastMissionIndexEnvelope = null;
let selectedMissionKey = '';
let selectedMissionAnchor = null;
let pendingMissionCopyAnchor = null;
let pendingMissionCopyAnchorClearTimer = 0;
const expandedSubagentParentKeys = new Set();
let expandedSubagentParentVersion = 0;
// Mission view state — three orthogonal row layers (activity / novelty / copy)
// plus one operator lifecycle pill. Artifact freshness still exists, but it
// does not own the row color; the row answers "running, finished, waiting, or
// inactive?" first. All state is derived per render from missionIndex + local
// short-lived memory; no AgentTraceMissionRow schema change.
const missionViewState = {
  initializedSeenKeys: false,    // first paint must not flag every row as new
  seenAtByKey: new Map(),        // key -> ms when this key first entered the index
  activeSeenByKey: new Map(),    // key -> bool: was rowHasActiveTrace on last observe
  completedTurnByKey: new Map(), // key -> latest completed turn index on last observe
  finishedAtByKey: new Map(),    // key -> ms when an active row completed/moved inactive
  copyByKey: new Map(),          // key -> { startedAt, successAt, failureAt, error }
};
const missionUncaughtErrors = [];
const MISSION_COPY_ACK_MS = 15_000;          // amber copy-confirmation flash
const MISSION_NEW_ROW_MS = 45_000;           // newly_seen visual decays after 45s
const MISSION_JUST_FINISHED_MS = 25 * 60_000; // finished stays blue until copied or aged out
const MISSION_RECENT_ACTIVITY_MS = 60_000;   // recent activity window
const MISSION_LIVE_ACTIVITY_MS = 2 * 60_000; // RUNNING requires recent source activity
const MISSION_IDLE_THRESHOLD_MS = 25 * 60_000;
const MISSION_PENDING_COPY_TTL_MS = 25 * 60_000;
const MISSION_LIFECYCLE_TICK_MS = 15_000;    // re-render while the dropdown is open
const MISSION_THREAD_QUIET_REFRESH_MS = 45_000;
const MISSION_AUTO_REFRESH_TICK_MS = 12_000;
// Heavy mission-index rebuild fallback. Cheap native source-mtime probes run
// every 3s while the workbench is open; this limits only full rebuild attempts.
const MISSION_AUTO_REFRESH_MIN_GAP_MS = 120_000;
const MISSION_REFRESH_WATCHDOG_MS = 20_000;
const MISSION_REFRESH_DEBOUNCE_MS = 750;
const MISSION_FOCUS_REFRESH_MIN_GAP_MS = 6_000;
const MISSION_TITLE_AUTHORITY_SYNC_MS = 3_000;
const MISSION_ROW_HEIGHT_PX = 58;
const MISSION_LANE_ROW_HEIGHT_PX = 28;
const MISSION_RENDER_OVERSCAN_ROWS = 22;
const MISSION_RENDER_WINDOW_STEP_ROWS = 10;
const MISSION_FAST_RENDER_OVERSCAN_ROWS = 42;
const MISSION_FAST_RENDER_WINDOW_STEP_ROWS = 24;
const MISSION_FAST_SCROLL_DELTA_PX = MISSION_ROW_HEIGHT_PX * 8;
const MISSION_FAST_SCROLL_MIN_PX_PER_MS = 1.2;
const MISSION_FAST_SCROLL_HOLD_MS = 420;
const MISSION_WINDOWING_MIN_ROWS = 96;
const MISSION_SCROLL_SETTLE_MS = 120;
const MISSION_RAIL_WHEEL_LINE_PX = 34;
const MISSION_RAIL_WHEEL_PAGE_RATIO = 0.82;
const MISSION_RAIL_WHEEL_MAX_STEP_PX = 420;
const MISSION_RAIL_WHEEL_MULTIPLIER = 1.08;
const MISSION_SCROLL_DEFER_RENDER_REASONS = new Set([
  'mission_index',
  'restore_scroll_window',
  'mission_measure_result',
]);
const TRACE_SCOPE_LARGE_BYTES = 512 * 1024;
const MISSION_OPERATOR_MARKER_STORAGE_KEY = 'aiw.agent_trace_structurer.operator_markers.v1';
let missionLifecycleTickTimer = 0;
let missionFinishedRefreshTimer = 0;
let missionAutoRefreshLastAt = 0;
let missionAutoRefreshSignatureByKey = new Map();
let missionRefreshDebounceTimer = 0;
let missionFocusRefreshLastAt = 0;
let missionTitleAuthoritySyncTimer = 0;
let missionRowsScrollRaf = 0;
let missionRowsUserScrollUntil = 0;
let missionRowsDeferredRenderTimer = 0;
let missionRowsDeferredRenderReason = '';
let missionRowsRenderRaf = 0;
let missionRowsRenderQueuedReason = '';
let missionRowsResizeObserver = null;
let missionRailWheelRaf = 0;
let missionRailWheelDeltaX = 0;
let missionRowsScrollAffordanceRaf = 0;
let missionRowsLastScrollTop = 0;
let missionRowsLastScrollAt = 0;
let missionRowsFastScrollUntil = 0;
let missionRowsRenderFragment = null;
let missionRowsRenderCache = null;
const missionRenderHeightPrefixCache = new WeakMap();
let lastMissionRowsRenderStats = { total: 0, rendered: 0, start: 0, end: 0, duration_ms: 0, windowed: false };
let lastMissionRowsScrollProfileStats = { profile: 'normal', overscan_rows: MISSION_RENDER_OVERSCAN_ROWS, window_step_rows: MISSION_RENDER_WINDOW_STEP_ROWS, fast_scrolling: false };
let lastMissionRowsDeferredRenderStats = { reason: '', delay_ms: 0, queued_at: 0, flushed_at: 0, count: 0 };
let lastMissionRowsScrollAffordance = { scrollable: false, edge: 'none', scroll_top: 0, max_scroll_top: 0 };
// v7 perf: render-scoped memo so missionAttentionForRow runs the heavy
// missionStateModel pipeline at most once per row per render. Previously it ran
// once inside the sort comparator (O(n log n)) AND once in the row forEach, with
// no caching — the dominant cause of the blank-pane stall while scrolling/filtering.
let missionAttentionMemo = new Map();
let missionAttentionMemoActive = false;
// v7 search: debounce the (heavy) re-render so fast typing does not stall the list.
let missionSearchRenderTimer = 0;
const MISSION_SEARCH_DEBOUNCE_MS = 80;
// v7 review lane: a soft evidence-quality red (missing diff, ui-only, commit-without
// -patch) on a row older than this drops out of "Needs Review Now" into Older/Finished
// so the lane keeps its label. Hard source blocks (source missing/schema mismatch)
// ignore this window and stay. Tunable.
const MISSION_REVIEW_FRESH_MS = 12 * 60 * 60_000;
const DEFAULT_AGENT_TRACE_SORT_MODE = 'dynamic';
let dropdownSortMode = DEFAULT_AGENT_TRACE_SORT_MODE;
let missionCopyReceiptHoldUntil = 0;
let missionIndexAutoRefreshTried = false;
let missionIndexRefreshPending = false;
let missionIndexRefreshQuiet = false;
let missionIndexRefreshQueued = false;
let missionIndexRefreshQueuedQuiet = false;
let missionIndexRefreshTimedOut = false;
let missionHttpIndexPending = false;
const missionSizeMeasurements = new Map();
const missionSizeMeasurementsPending = new Set();
let missionIndexRefreshQueuedReason = '';
let missionIndexRefreshStartedAt = 0;
let missionIndexRefreshTimer = 0;
let showInactiveMissions = false;
let windowShellDefaultDropdownPending = false;
const variantArtifactOverlay = new Map();
let missionOperatorMarkers = loadMissionOperatorMarkers();
const MISSION_ATTENTION_LANES = Object.freeze([
  ['needs_review_now', 'Needs Review Now'],
  ['ready_to_copy', 'Ready To Copy / Paste To Type B'],
  ['waiting_on_operator', 'Waiting On Operator / Type B Response'],
  ['rogue_active', 'Rogue Active / Suspicious'],
  ['running_background_goals', 'Running Background Goals'],
  ['paused_deferred', 'Paused / Deferred'],
  ['older_finished_copied', 'Older Finished / Copied'],
  ['retired', 'Retired'],
]);
// Dynamic ("most useful first") tiers — the default sort, rendered as one flat
// most-useful-first list (lane headers belong to the Review queue). Higher tier
// = nearer the top; within a tier the most-recently-active mission wins. The
// tier answers "why would I want to look at this now?":
//   pinned/due (operator-elevated) > live fleet > mid-handoff > fresh blocker >
//   ready-to-copy > recent work > done/idle > snoozed > retired.
// Liveness is read from lifecycle/runtime state, NOT the attention lane: an
// actively-running mission folds into the needs_review_now lane (its in-flight
// turn needs a refresh-before-copy), so a lane-only sort cannot surface the live
// fleet. This is the fix for running missions being buried under the finished
// review/copy backlog in the old review_first ordering.
function missionDynamicTier(attn) {
  const marker = attn.operator_marker || {};
  const act = attn.view_activity; // 'live' | 'checking' | 'idle' | 'just_finished' | 'recent' | 'warm' | ...
  if (attn.lane === 'retired' || attn.attention_state === 'retired') return 0;
  if (marker.pinned) return 100;                          // operator override: keep on top
  if (attn.follow_up_due?.due) return 95;                 // operator reminder is now due
  if (marker.snoozed_until_ms && Number(marker.snoozed_until_ms) > Date.now()) return 5;
  // Genuinely live == the RUNNING pill (lifecycle_state 'running' <=> view
  // activity 'live'). Do NOT treat runtime_state 'running_active_turn' or the
  // rogue_active lane as live: both linger as a stale cache on interrupted/idle
  // rows, which is what pushed INACTIVE rows above real running missions.
  if (act === 'live' || attn.lifecycle_state === 'running'
      || attn.lane === 'running_background_goals') return 80;   // live fleet — running now
  if (attn.copy_state === 'pending_after_copy'
      || attn.copy_state === 'just_copied'
      || attn.lane === 'waiting_on_operator') return 70;        // mid-handoff, waiting on you
  // Anything the cockpit cannot confirm as active sinks BELOW recent finished +
  // actionable work, no matter what risk/lane the attention model assigned it:
  // idle ("INACTIVE": no source activity 25m+), checking/stale-active cache,
  // paused, and older rows. An inactive/unconfirmed mission must never outrank a
  // running OR a fresh finished one — this is the reported regression.
  if (act === 'idle' || attn.lane === 'paused_deferred') return 12;
  if (act === 'checking' || attn.lane === 'rogue_active') return 14;
  if (attn.lane === 'older_finished_copied') return 10;
  // Live-or-recent and actionable:
  if (attn.risk_state === 'red' && attn.attention_state === 'review_now') return 60; // fresh blocker
  if (attn.attention_state === 'copy_ready'
      || attn.lane === 'ready_to_copy') return 50;              // finished, ready to copy
  return 40;                                                    // recent finished / known work
}
const SOURCE_WINDOW_PROMPT_CYCLE = 'latest_prompt_cycle';
const SOURCE_WINDOW_SELECTED_TURN = 'selected_turn';
const SOURCE_WINDOW_FULL_THREAD = 'full_thread';
const SOURCE_WINDOW_FULL_THREAD_CONCISE = 'full_thread_concise';
const DEFAULT_TRACE_SOURCE_WINDOW = SOURCE_WINDOW_PROMPT_CYCLE;
const TRACE_OPERATOR_SOURCE_WINDOWS = [SOURCE_WINDOW_PROMPT_CYCLE, SOURCE_WINDOW_FULL_THREAD_CONCISE, SOURCE_WINDOW_FULL_THREAD];
const EXPECTED_VARIANT_SCHEMAS = Object.freeze({
  trace_capsule: 'agent_trace_capsule_text_v3',
  closeout_report: 'agent_trace_closeout_report_v1',
  packet: 'agent_trace_packet_v1',
  denoised: 'agent_trace_tape_v1',
  compact_json: 'agent_trace_compact_json_v2',
});
const EXPECTED_VARIANT_ROLES = Object.freeze({
  trace_capsule: 'trace_capsule',
  closeout_report: 'closeout_report',
  packet: 'operator_handoff_packet',
  denoised: 'trace_tape',
  compact_json: 'sidecar_compaction_input',
});
const VARIANT_SIZE_BUDGETS = Object.freeze({
  trace_capsule: 0,
  closeout_report: 0,
  packet: 64 * 1024,
  denoised: 12 * 1024,
  compact_json: 32 * 1024,
});
const missionRailEl = document.getElementById('mission-rail');
const selectedMissionEl = document.getElementById('selected-mission');
const copyCompressedBtn = document.getElementById('copy-compressed');
const copyFullBtn = document.getElementById('copy-full');
const revealMissionBtn = document.getElementById('reveal-mission');
const refreshMissionsBtn = document.getElementById('refresh-missions');

function resourceFreshnessPayload() {
  return window.__aiwResourceFreshness || { status: 'unknown', ok: false, mismatch_count: 0 };
}

function isResourceBundleStale() {
  return resourceFreshnessPayload().status === 'stale';
}

function applyResourceFreshnessWarning() {
  const freshness = resourceFreshnessPayload();
  document.body.dataset.resourceFreshness = freshness.status || 'unknown';
  if (freshness.status !== 'stale') return;
  const kicker = document.querySelector('.kicker');
  if (kicker) kicker.textContent = 'Agent Trace Structurer · stale installed bundle';
  const sub = document.querySelector('.sub');
  const mismatch = Number.isFinite(freshness.mismatch_count) ? freshness.mismatch_count : (freshness.mismatches || []).length;
  if (sub) sub.textContent = `Reinstall required before testing (${mismatch || 1} resource mismatch).`;
  if (els.status) els.status.textContent = 'Installed app bundle differs from repo source.';
}

applyResourceFreshnessWarning();

function missionReceiptEl() {
  return document.getElementById('mission-receipt');
}

function shouldPreserveMissionCopyReceipt(text, state = '') {
  if (state === 'copy_success' || state === 'copy_error') return false;
  const receipt = missionReceiptEl();
  if (!receipt || receipt.dataset.state !== 'copy_success') return false;
  if (Date.now() >= missionCopyReceiptHoldUntil) return false;
  return /^(Refreshing|Auto-refreshing|Refresh already running|✓ Refreshed|✓ Auto-refreshed|✓ Source index changed|✗ Refresh failed)/.test(String(text || ''));
}

function setMissionReceipt(text, state = '') {
  if (shouldPreserveMissionCopyReceipt(text, state)) return;
  const receipt = missionReceiptEl();
  if (receipt) {
    receipt.textContent = text;
    if (state) receipt.dataset.state = state;
    else delete receipt.dataset.state;
  }
  if (state === 'copy_success') missionCopyReceiptHoldUntil = Date.now() + MISSION_COPY_ACK_MS;
  else if (state === 'copy_error') missionCopyReceiptHoldUntil = 0;
  if (els.status) els.status.textContent = text;
}

function setMissionRefreshControlsDisabled(disabled) {
  if (refreshMissionsBtn) refreshMissionsBtn.disabled = disabled;
  const dropdownRefresh = document.getElementById('agent-trace-refresh');
  if (dropdownRefresh) dropdownRefresh.disabled = disabled;
  const paneRefresh = document.getElementById('mission-pane-refresh');
  if (paneRefresh) paneRefresh.disabled = disabled;
}

function rememberUncaughtWorkbenchError(kind, error) {
  const message = error?.message || String(error || 'unknown error');
  missionUncaughtErrors.push({
    kind: String(kind || 'error'),
    message,
    at: new Date().toISOString(),
  });
  while (missionUncaughtErrors.length > 25) missionUncaughtErrors.shift();
  try { console.error('[agent-trace-workbench]', kind, error); } catch (_) {}
  return message;
}

function guardAgentTraceAction(kind, fn) {
  try {
    return fn();
  } catch (error) {
    const message = rememberUncaughtWorkbenchError(kind, error);
    setMissionReceipt(`Action failed (${String(kind || 'action').replace(/_/g, ' ')}): ${message}. Try Refresh, latest response bundle, or Save + Reveal.`);
    setMissionRefreshControlsDisabled(false);
    safeRenderAgentTraceDropdown(`guarded_${kind || 'action'}`);
    return null;
  }
}

window.addEventListener('error', (event) => {
  rememberUncaughtWorkbenchError('uncaught_error', event?.error || event?.message || event);
});
window.addEventListener('unhandledrejection', (event) => {
  rememberUncaughtWorkbenchError('unhandled_rejection', event?.reason || event);
});

function _formatDurationMs(ms) {
  const n = Number(ms || 0);
  if (!Number.isFinite(n) || n <= 0) return '0 ms';
  if (n < 1000) return `${Math.round(n)} ms`;
  return `${(n / 1000).toFixed(n < 10000 ? 1 : 0)} s`;
}

function captureMissionListViewState() {
  return {
    selectedKey: selectedMissionKey,
    selectedAnchor: selectedMissionAnchor,
    railScrollTop: missionRailEl ? missionRailEl.scrollTop : 0,
    dropdownScrollTop: dropdownEls?.agentTraceRows ? dropdownEls.agentTraceRows.scrollTop : 0,
    dropdownSearch,
    dropdownSearchValue: dropdownEls?.agentTraceSearch ? dropdownEls.agentTraceSearch.value : '',
  };
}

function restoreMissionListViewState(state) {
  if (!state) return;
  const searchValue = state.dropdownSearchValue ?? state.dropdownSearch ?? '';
  dropdownSearch = searchValue;
  if (dropdownEls?.agentTraceSearch && dropdownEls.agentTraceSearch.value !== searchValue) {
    dropdownEls.agentTraceSearch.value = searchValue;
  }
  const searchMatch = searchValue ? bestMissionSearchMatch(searchValue) : null;
  const selectedStillMatchesSearch = searchValue && state.selectedKey
    ? missionRowMatchesSearch(findMissionByKey(state.selectedKey), searchValue)
    : false;
  if (restoreMissionAnchor(pendingMissionCopyAnchor)) {
    // Copy/capture callbacks trigger mission-index refreshes. While a copy
    // anchor is held, background refresh state must not steal the visible
    // selection back to the newest active trace.
  } else if (selectedStillMatchesSearch && findMissionByKey(state.selectedKey)) {
    selectedMissionKey = state.selectedKey;
    rememberSelectedMissionAnchor();
  } else if (searchMatch) {
    selectedMissionKey = missionKey(searchMatch);
    selectedMissionAnchor = missionAnchor(searchMatch);
  } else if (state.selectedKey && findMissionByKey(state.selectedKey)) {
    selectedMissionKey = state.selectedKey;
    rememberSelectedMissionAnchor();
  } else if (!restoreMissionAnchor(state.selectedAnchor)) {
    ensureSelectedMission();
  }
  window.requestAnimationFrame(() => {
    if (missionRailEl) missionRailEl.scrollTop = state.railScrollTop || 0;
    if (dropdownEls?.agentTraceRows) dropdownEls.agentTraceRows.scrollTop = state.dropdownScrollTop || 0;
    if (isAgentTraceWorkbenchActive() && dropdownEls?.agentTraceRows && lastMissionRowsRenderStats.windowed) {
      safeRenderAgentTraceDropdown('restore_scroll_window');
    }
  });
}

function beginMissionIndexRefresh(reason = 'manual', { quiet = false } = {}) {
  missionIndexRefreshPending = true;
  missionIndexRefreshQuiet = Boolean(quiet);
  missionIndexRefreshTimedOut = false;
  missionIndexRefreshStartedAt = Date.now();
  if (missionIndexRefreshTimer) {
    window.clearTimeout(missionIndexRefreshTimer);
    missionIndexRefreshTimer = 0;
  }
  setMissionRefreshControlsDisabled(true);
  const suffix = reason && reason !== 'manual' ? ` (${reason.replace(/_/g, ' ')})` : '';
  setMissionReceipt(`${missionIndexRefreshQuiet ? 'Auto-refreshing' : 'Refreshing'} missions${suffix}…`);
  missionIndexRefreshTimer = window.setTimeout(() => {
    missionIndexRefreshTimer = 0;
    if (!missionIndexRefreshPending) return;
    const elapsed = Math.max(1, Math.round((Date.now() - missionIndexRefreshStartedAt) / 1000));
    const cachedRows = Array.isArray(missionIndex?.active_rows) ? missionIndex.active_rows.length : 0;
    missionIndexRefreshPending = false;
    missionIndexRefreshQuiet = false;
    missionIndexRefreshTimedOut = true;
    setMissionRefreshControlsDisabled(false);
    setMissionReceipt(`Still refreshing after ${elapsed}s; controls unlocked; showing ${cachedRows} cached missions.`);
    requestMissionIndex('refresh_watchdog_cached_index');
  }, MISSION_REFRESH_WATCHDOG_MS);
}

function finishMissionIndexRefresh(data) {
  if (!missionIndexRefreshPending && !(missionIndexRefreshTimedOut && data?.native_refresh_started_at)) return;
  const elapsedMs = missionIndexRefreshStartedAt ? (Date.now() - missionIndexRefreshStartedAt) : 0;
  const wasQuiet = missionIndexRefreshQuiet;
  const wasTimedOut = missionIndexRefreshTimedOut;
  missionIndexRefreshPending = false;
  missionIndexRefreshQuiet = false;
  missionIndexRefreshTimedOut = false;
  if (missionIndexRefreshTimer) {
    window.clearTimeout(missionIndexRefreshTimer);
    missionIndexRefreshTimer = 0;
  }
  setMissionRefreshControlsDisabled(false);
  if (data?.ok && data.index) {
    const rows = Array.isArray(data.index.active_rows) ? data.index.active_rows.length : 0;
    const goals = Number(data.index.active_goal_thread_count ?? data.index.active_goal_count ?? 0);
    const goalText = Number.isFinite(goals) && goals > 0 ? ` · ${goals} goals` : '';
    const generatedAt = parseTimestamp(data.index.generated_at);
    const stamp = generatedAt ? ` · ${formatClockLabel(data.index.generated_at)}` : '';
    const perf = data.index.perf || {};
    const cache = perf.summary_cache || {};
    const durationMs = data.native_refresh_duration_ms || perf.duration_ms || elapsedMs;
    const cacheText = cache.hits != null
      ? ` · cache ${cache.hits || 0} hit/${cache.misses || 0} miss/${cache.stale || 0} stale`
      : '';
    const queuedText = missionIndexRefreshQueued ? ' · queued next refresh' : '';
    const verb = wasTimedOut ? 'Background refreshed' : (wasQuiet ? 'Auto-refreshed' : 'Refreshed');
    setMissionReceipt(`✓ ${verb} ${rows} missions${goalText} in ${_formatDurationMs(durationMs)}${cacheText}${stamp}${queuedText}`);
    return;
  }
  const stage = data?.stage ? `${data.stage}: ` : '';
  setMissionReceipt(`✗ Refresh failed: ${stage}${data?.error || 'mission index unavailable'}`);
}

function missionProviderKey(provider) {
  return provider === 'claude' ? 'claude_code' : (provider || '');
}

function missionKeyFromParts(provider, sessionId) {
  return `${missionProviderKey(provider)}:${sessionId || ''}`;
}

function missionKey(row) {
  const fallbackId = row?.session_id || row?.source_path || row?.path || row?.title || row?.short_label || '';
  return missionKeyFromParts(row?.provider, fallbackId);
}

function titleHasOldRetirePrefix(value) {
  return reducerTitleHasOldRetirePrefix(value);
}

function rowHasOldRetirePrefix(row) {
  return titleHasOldRetirePrefix(row?.source_title)
    || titleHasOldRetirePrefix(row?.display_title)
    || titleHasOldRetirePrefix(row?.title)
    || titleHasOldRetirePrefix(row?.short_label);
}

function rowIsOldPrefixRetired(row) {
  const view = missionViewStateForRow(row);
  return Boolean(view?.retired);
}

function missionDisplayTitle(row, displayTurn = null) {
  return reducerMissionDisplayTitle(row || {}, displayTurn || {});
}

function missionPromptPreview(row, displayTurn = null) {
  return reducerMissionPromptPreview(row || {}, displayTurn || {});
}

function missionAnchor(row) {
  if (!row) return null;
  const lct = traceDisplayTurn(row);
  const traceWindow = lct.trace_window || {};
  return {
    key: missionKey(row),
    provider: row.provider || '',
    session_id: row.session_id || '',
    title: missionDisplayTitle(row, lct),
    prompt_sha16: traceWindow.prompt_sha16 || lct.trace_window_prompt_sha16 || lct.prompt_sha16 || '',
    turn_index: traceWindow.end_turn_index ?? lct.turn_index ?? null,
    turn_id: traceWindow.turn_id || lct.trace_window_turn_id || lct.turn_id || '',
    window_start_turn_index: traceWindow.start_turn_index ?? lct.turn_index ?? null,
    window_turn_count: traceWindow.turn_count ?? 1,
  };
}

function missionSubagentDeployments(row) {
  return Array.isArray(row?.subagent_deployments) ? row.subagent_deployments : [];
}

function missionSubagentCount(row) {
  const declared = Number(row?.subagent_summary?.count || 0);
  const observed = missionSubagentDeployments(row).length;
  return Number.isFinite(declared) && declared > observed ? declared : observed;
}

function missionSubagentLinkedCount(row) {
  const declared = Number(row?.subagent_summary?.linked_trace_count || 0);
  const observed = missionSubagentDeployments(row).filter(dep => dep?.linked_child_trace).length;
  return Number.isFinite(declared) && declared > observed ? declared : observed;
}

function missionSubagentLabel(dep) {
  return String(dep?.label || dep?.description || dep?.subagent_type || dep?.tool_name || 'Sub-agent').trim();
}

function missionSubagentRelationshipKind(dep) {
  return dep?.relationship_kind || dep?.relationship?.kind || (dep?.linked_child_trace ? 'linked_sidechain' : 'deployment_only');
}

function missionSubagentStatusLabel(dep) {
  const kind = missionSubagentRelationshipKind(dep);
  if (kind === 'linked_sidechain') return 'LINKED';
  if (kind === 'sidechain_only') return 'TRACE ONLY';
  return 'DEPLOYED';
}

function missionSubagentTraceStats(dep) {
  const trace = dep?.child_trace || {};
  const bits = [];
  if (trace.agent_id || dep?.agent_id) bits.push(String(trace.agent_id || dep.agent_id).slice(0, 8));
  if (trace.attribution_agent || dep?.attribution_agent) bits.push(trace.attribution_agent || dep.attribution_agent);
  if (trace.turn_count != null) bits.push(`${trace.turn_count}t`);
  if (trace.tool_count != null) bits.push(`${trace.tool_count} tools`);
  if (trace.error_count) bits.push(`${trace.error_count} err`);
  return bits.filter(Boolean).join(' · ');
}

function missionSubagentTargetMissionKey(dep) {
  const trace = dep?.child_trace || {};
  const provider = trace.provider || dep?.provider || '';
  const sessionId = trace.session_id || trace.agent_id || dep?.agent_id || '';
  if (!provider || !sessionId) return '';
  const key = missionKeyFromParts(provider, sessionId);
  return findMissionByKey(key) ? key : '';
}

function missionSubagentSearchText(row) {
  const parts = [];
  for (const dep of missionSubagentDeployments(row)) {
    const trace = dep?.child_trace || {};
    parts.push(
      missionSubagentLabel(dep),
      dep?.subagent_type || '',
      dep?.model || '',
      dep?.prompt_preview || '',
      dep?.tool_call_id || '',
      trace.session_id || '',
      trace.agent_id || '',
      trace.prompt_title || '',
      trace.prompt_preview || '',
      trace.parent_session_id || '',
    );
  }
  return parts.filter(Boolean).join(' ');
}

function missionSubagentOperatorText(row) {
  const count = missionSubagentCount(row);
  if (!count) return '';
  const linked = missionSubagentLinkedCount(row);
  const labels = missionSubagentDeployments(row).slice(0, 3).map(missionSubagentLabel).filter(Boolean);
  const labelText = labels.length ? `: ${labels.join(', ')}` : '';
  const linkedText = linked ? `, ${linked} linked trace${linked === 1 ? '' : 's'}` : '';
  return `sub-agents ${count}${linkedText}${labelText}`;
}

function missionShouldExpandSubagents(row, { expandedParentKeys = expandedSubagentParentKeys, forceExpandSubagents = false } = {}) {
  if (!missionSubagentDeployments(row).length) return false;
  if (forceExpandSubagents) return true;
  return expandedParentKeys.has(missionKey(row));
}

function toggleMissionSubagents(key) {
  const k = String(key || '');
  if (!k) return false;
  if (expandedSubagentParentKeys.has(k)) expandedSubagentParentKeys.delete(k);
  else expandedSubagentParentKeys.add(k);
  expandedSubagentParentVersion += 1;
  return true;
}

function pruneExpandedSubagentParents(rows) {
  const liveKeys = new Set((Array.isArray(rows) ? rows : []).map(missionKey).filter(Boolean));
  let pruned = false;
  expandedSubagentParentKeys.forEach((key) => {
    if (!liveKeys.has(key)) {
      expandedSubagentParentKeys.delete(key);
      pruned = true;
    }
  });
  if (pruned) expandedSubagentParentVersion += 1;
}

function missionGoal(row) {
  const goal = row?.goal || {};
  if (row?.has_goal || goal.goal_id || goal.status) return goal;
  return null;
}

function missionGoalStatus(row) {
  return String(missionGoal(row)?.status || row?.goal_status || '').toLowerCase();
}

function missionGoalSortPriority(row) {
  const direct = Number(row?.goal_sort_priority || 0);
  if (Number.isFinite(direct) && direct > 0) return direct;
  return {
    active: 40,
    usage_limited: 30,
    budget_limited: 30,
    paused: 20,
    blocked: 10,
    complete: 0,
  }[missionGoalStatus(row)] || 0;
}

function rowHasActiveGoal(row) {
  return missionGoalStatus(row) === 'active'
    || String(row?.goal_fleet_control?.observed_status || '').toLowerCase() === 'active';
}

function rowIsLiveMission(row) {
  return rowHasActiveTrace(row) || rowHasActiveGoal(row);
}

function missionGoalOperatorText(row) {
  const goal = missionGoal(row);
  if (!goal) return '';
  const status = String(goal.status || 'goal').replace(/_/g, ' ');
  const used = Number(goal.tokens_used || 0);
  const budget = Number(goal.token_budget || 0);
  const tokens = budget > 0
    ? `${Math.round((used / budget) * 100)}% token budget`
    : (used > 0 ? `${used.toLocaleString()} tokens` : '');
  const objective = String(goal.objective_preview || '').trim();
  const control = missionGoalFleetControl(row);
  const decision = control?.decision_label ? `fleet: ${control.decision_label}` : '';
  return [`goal ${status}`, tokens, objective, decision].filter(Boolean).join(' · ');
}

function missionGoalFleetControl(row) {
  const direct = row?.goal_fleet_control;
  if (direct && typeof direct === 'object') return direct;
  const goal = missionGoal(row);
  const nested = goal?.goal_fleet_control || goal?.fleet_control;
  return nested && typeof nested === 'object' ? nested : {};
}

function missionGoalFleetAction(row) {
  return String(missionGoalFleetControl(row)?.next_allowed_action || '').trim();
}

function goalFleetState() {
  const state = missionIndex?.goal_fleet_state;
  return state && typeof state === 'object' ? state : {};
}

function goalFleetSummaryText() {
  const state = goalFleetState();
  const decisions = state.decision_counts || {};
  const fanIn = Number(state.fan_in_needed_count || 0);
  const blocked = Number(decisions.capture_or_reroute_blocker || 0);
  const readMore = Number(decisions.read_more || 0);
  const parts = [];
  if (fanIn > 0) parts.push(`fan-in ${fanIn}`);
  if (blocked > 0) parts.push(`blocked ${blocked}`);
  if (readMore > 0) parts.push(`read ${readMore}`);
  return parts.join(' · ');
}

function missionGoalChip(row) {
  const goal = missionGoal(row);
  if (!goal) return '';
  const status = missionGoalStatus(row) || 'goal';
  const label = status === 'active' ? 'GOAL' : status.replace(/_/g, ' ').toUpperCase().slice(0, 12);
  return `<span class="goal-chip" title="${_escHtml(missionGoalOperatorText(row))}">${_escHtml(label)}</span>`;
}

function missionGoalThreads() {
  return Array.isArray(missionIndex?.goal_threads) ? missionIndex.goal_threads : [];
}

function missionGoalThreadCount() {
  const direct = Number(missionIndex?.goal_thread_count);
  if (Number.isFinite(direct) && direct >= 0) return direct;
  const legacy = Number(missionIndex?.goal_count);
  if (Number.isFinite(legacy) && legacy >= 0) return legacy;
  return missionGoalThreads().length;
}

function activeGoalThreadCount() {
  const direct = Number(missionIndex?.active_goal_thread_count);
  if (Number.isFinite(direct) && direct >= 0) return direct;
  const legacy = Number(missionIndex?.active_goal_count);
  if (Number.isFinite(legacy) && legacy >= 0) return legacy;
  return missionGoalThreads().filter(goal => String(goal?.status || '').toLowerCase() === 'active').length;
}

function missionGoalSummaryText() {
  const active = activeGoalThreadCount();
  const total = missionGoalThreadCount();
  const fleet = goalFleetSummaryText();
  const base = !active && !total
    ? ''
    : (total && total !== active ? `goals ${active}/${total}` : `goals ${active || total}`);
  return [base, fleet].filter(Boolean).join(' · ');
}

function normalizeMissionSearchText(value) {
  return String(value || '')
    .toLowerCase()
    .normalize('NFKD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/[^a-z0-9]+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

function collectMissionSearchText(value, out = [], depth = 0) {
  if (out.join(' ').length > 16000 || depth > 5 || value == null) return out;
  if (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean') {
    const text = String(value || '').trim();
    if (text) out.push(text.slice(0, 1000));
    return out;
  }
  if (Array.isArray(value)) {
    value.slice(0, 60).forEach((item) => collectMissionSearchText(item, out, depth + 1));
    return out;
  }
  if (typeof value === 'object') {
    const preferred = [
      'title', 'display_title', 'source_title', 'operator_alias', 'short_label',
      'session_id', 'provider', 'prompt_preview', 'objective', 'objective_preview',
      'thread_source', 'parent_thread_id', 'parent_session_id', 'parent_title',
      'goal_status', 'status', 'path', 'session_file', 'item_path', 'artifact_path',
      'source_clip_path', 'clip_path', 'sha16', 'source_sha16', 'prompt_sha16',
      'commit', 'commit_hash', 'cap_id', 'work_item_id', 'closeout', 'summary',
      'description', 'label', 'tool_call_id', 'subagent_type', 'model',
    ];
    preferred.forEach((key) => {
      if (Object.prototype.hasOwnProperty.call(value, key)) collectMissionSearchText(value[key], out, depth + 1);
    });
    Object.entries(value).slice(0, 80).forEach(([key, item]) => {
      if (/^(title|display|source|prompt|goal|objective|path|file|artifact|commit|sha|hash|cap|work|closeout|subagent|session|provider|attachment|status|marker|mission)/i.test(key)) {
        out.push(key);
        collectMissionSearchText(item, out, depth + 1);
      }
    });
  }
  return out;
}

function missionSearchHaystack(row) {
  const displayTurn = activityDisplayTurn(row);
  const marker = missionOperatorMarker(row);
  const ordinal = row?.mission_ordinal_key != null ? `mission ${row.mission_ordinal_key} #${row.mission_ordinal_key}` : '';
  return normalizeMissionSearchText([
    missionDisplayTitle(row, displayTurn),
    missionPromptPreview(row, displayTurn),
    row?.short_label || '',
    row?.session_id || '',
    row?.provider || '',
    ordinal,
    row?.goal_status || '',
    row?.goal?.objective_preview || '',
    row?.goal?.objective || '',
    missionSubagentSearchText(row),
    collectMissionSearchText(row).join(' '),
    collectMissionSearchText(marker).join(' '),
  ].join(' '));
}

function missionRowMatchesSearch(row, q) {
  if (!q) return true;
  return missionSearchScore(row, q) > 0;
}

function _escapeRegExp(value) {
  return String(value || '').replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

function _missionTitleIdentityTexts(row) {
  const displayTurn = activityDisplayTurn(row);
  return [
    missionDisplayTitle(row, displayTurn),
    row?.display_title,
    row?.source_title,
    row?.operator_alias,
    row?.title,
    row?.short_label,
    row?.parent_title,
  ].map((value) => String(value || '').trim()).filter(Boolean);
}

function _missionNumericIdentityTokens(row) {
  const tokens = new Set();
  const add = (value) => {
    const text = String(value ?? '').trim();
    if (/^\d+$/.test(text)) tokens.add(text);
  };
  add(row?.mission_ordinal_key);
  for (const raw of _missionTitleIdentityTexts(row)) {
    const text = normalizeMissionSearchText(raw);
    add(text);
    const leading = text.match(/^(?:thread\s+|mission\s+)?(\d+)(?:\s|$)/);
    if (leading) add(leading[1]);
  }
  return tokens;
}

function missionNumericSearchScore(row, token) {
  const value = String(token || '').trim();
  if (!/^\d+$/.test(value)) return 0;
  const identities = _missionNumericIdentityTokens(row);
  if (identities.has(value)) return 1_000_000_000;
  if (value.length >= 2 && Array.from(identities).some((item) => item.startsWith(value))) return 100_000_000;
  const exactWord = new RegExp(`(^|\\s)${_escapeRegExp(value)}($|\\s)`);
  return exactWord.test(missionSearchHaystack(row)) ? 20 : 0;
}

function missionSearchMatchSource(row, q, score = missionSearchScore(row, q)) {
  const query = normalizeMissionSearchText(q);
  if (!query) return 'none';
  const tokens = _missionSearchTokens(query);
  if (tokens.some((token) => /^\d+$/.test(token) && missionNumericSearchScore(row, token) >= 100_000_000)) {
    return 'exact title/thread number';
  }
  const displayTurn = activityDisplayTurn(row);
  const title = normalizeMissionSearchText(missionDisplayTitle(row, displayTurn));
  if (title && title.includes(query)) return 'title';
  const prompt = normalizeMissionSearchText(missionPromptPreview(row, displayTurn));
  if (prompt && prompt.includes(query)) return 'prompt';
  const sessionId = normalizeMissionSearchText(row?.session_id || '');
  if (sessionId && sessionId.includes(query)) return 'session id';
  if (score > 0) return 'expanded provenance index';
  return 'no match';
}

function _missionSearchTokens(q) {
  return normalizeMissionSearchText(q)
    .split(/\s+/)
    .map((t) => t.trim())
    .filter((t) => t && (t.length > 1 || /\d/.test(t)));
}

// Bidirectional, typo-tolerant token match so "structurer" finds "structure",
// "race" finds "trace", and a trailing-character slip still lands. Returns a
// per-token contribution (0 = miss); higher = stronger.
function _fuzzyTokenScore(token, haystack) {
  if (!token) return 0;
  if (haystack.includes(token)) return 100;
  if (token.length >= 4) {
    const stem = token.slice(0, Math.max(4, token.length - 2));
    if (haystack.includes(stem)) return 60;
  }
  // ordered subsequence (loose fuzzy): characters of token appear in order
  let i = 0;
  for (let c = 0; c < haystack.length && i < token.length; c += 1) {
    if (haystack[c] === token[i]) i += 1;
  }
  return i === token.length ? 25 : 0;
}

// v7 ordinal-first ranking: typing a mission number pins that mission to the top,
// then title/body matches; every query token must hit somewhere (AND semantics).
function missionSearchScore(row, q) {
  const query = normalizeMissionSearchText(q);
  if (!query) return 1;
  if (/^\d+$/.test(query)) return missionNumericSearchScore(row, query);
  const haystack = missionSearchHaystack(row);
  const tokens = _missionSearchTokens(query);
  if (!tokens.length) return haystack.includes(query) ? 100 : 0;
  let total = 0;
  for (const token of tokens) {
    if (/^\d+$/.test(token)) {
      const numericScore = missionNumericSearchScore(row, token);
      if (!numericScore) return 0;
      total += numericScore;
      continue;
    }
    const s = _fuzzyTokenScore(token, haystack);
    if (!s) return 0;
    total += s;
  }
  return total;
}

function bestMissionSearchMatch(q, sourceRows = (String(q || '').trim() ? allMissionRows() : visibleMissionRows())) {
  const scored = (Array.isArray(sourceRows) ? sourceRows : [])
    .map((row) => [row, missionSearchScore(row, q)])
    .filter((entry) => entry[1] > 0);
  if (!scored.length) return null;
  scored.sort((a, b) => (b[1] - a[1])
    || (_missionSortTime(b[0]) - _missionSortTime(a[0]))
    || ((b[0].mission_ordinal_key || 0) - (a[0].mission_ordinal_key || 0)));
  return scored[0][0] || null;
}

function missionRenderRows(rows, options = {}) {
  const out = [];
  let previousLane = '';
  const includeLanes = options.includeAttentionLanes === true;
  for (const row of Array.isArray(rows) ? rows : []) {
    if (includeLanes) {
      const lane = missionAttentionForRow(row, options.renderStart || Date.now()).lane;
      if (lane && lane !== previousLane) {
        out.push({ kind: 'lane', lane, label: missionAttentionLaneLabel(lane) });
        previousLane = lane;
      }
    }
    out.push({ kind: 'mission', row });
    if (!missionShouldExpandSubagents(row, options)) continue;
    const deployments = missionSubagentDeployments(row);
    for (const dep of deployments) {
      const depKey = [
        missionKey(row),
        'subagent',
        dep?.tool_call_id || dep?.turn_index || '',
        dep?.deployment_index || dep?.tool_index || out.length,
      ].join(':');
      out.push({ kind: 'subagent', row, deployment: dep, key: depKey });
    }
  }
  return out;
}

function clearPendingMissionCopyAnchor(anchor = null) {
  if (pendingMissionCopyAnchorClearTimer) {
    window.clearTimeout(pendingMissionCopyAnchorClearTimer);
    pendingMissionCopyAnchorClearTimer = 0;
  }
  if (!anchor || pendingMissionCopyAnchor === anchor) {
    pendingMissionCopyAnchor = null;
  }
}

function holdPendingMissionCopyAnchor(anchor, holdMs = 300000) {
  clearPendingMissionCopyAnchor();
  pendingMissionCopyAnchor = anchor || null;
  if (!pendingMissionCopyAnchor) return;
  pendingMissionCopyAnchorClearTimer = window.setTimeout(() => {
    pendingMissionCopyAnchorClearTimer = 0;
    if (pendingMissionCopyAnchor === anchor) pendingMissionCopyAnchor = null;
  }, holdMs);
}

function rememberSelectedMissionAnchor() {
  const row = findMissionByKey(selectedMissionKey);
  if (row) selectedMissionAnchor = missionAnchor(row);
}

function restoreMissionAnchor(anchor) {
  if (!anchor) return false;
  const rows = allMissionRows();
  const providerKey = missionProviderKey(anchor.provider);
  const title = String(anchor.title || '').trim().toLowerCase();
  const candidates = [
    rows.find((row) => missionKey(row) === anchor.key),
    rows.find((row) => row.session_id === anchor.session_id && missionProviderKey(row.provider) === providerKey),
    rows.find((row) => {
      const lct = traceDisplayTurn(row);
      return anchor.prompt_sha16 && lct.prompt_sha16 === anchor.prompt_sha16 && Number(lct.turn_index) === Number(anchor.turn_index);
    }),
    rows.find((row) => title && String(missionDisplayTitle(row, traceDisplayTurn(row))).trim().toLowerCase() === title),
  ].filter(Boolean);
  const row = candidates[0] || null;
  if (!row) return false;
  selectedMissionKey = missionKey(row);
  selectedMissionAnchor = missionAnchor(row);
  return true;
}

function ensureSelectedMission(fallbackRows = sortedMissionRows(activeMissionRows())) {
  if (restoreMissionAnchor(pendingMissionCopyAnchor)) return;
  if (selectedMissionKey && findMissionByKey(selectedMissionKey)) {
    rememberSelectedMissionAnchor();
    return;
  }
  if (restoreMissionAnchor(selectedMissionAnchor)) return;
  const first = fallbackRows[0] || sortedMissionRows(activeMissionRows())[0] || null;
  if (first) {
    selectedMissionKey = missionKey(first);
    selectedMissionAnchor = missionAnchor(first);
  }
}

function ensureSelectedMissionInRows(fallbackRows = []) {
  const rows = Array.isArray(fallbackRows) ? fallbackRows : [];
  const rowKeys = new Set(rows.map((row) => missionKey(row)).filter(Boolean));
  if (restoreMissionAnchor(pendingMissionCopyAnchor) && rowKeys.has(selectedMissionKey)) return;
  if (selectedMissionKey && rowKeys.has(selectedMissionKey)) {
    rememberSelectedMissionAnchor();
    return;
  }
  const first = rows[0] || null;
  if (first) {
    selectedMissionKey = missionKey(first);
    selectedMissionAnchor = missionAnchor(first);
    return;
  }
  ensureSelectedMission(rows);
}

function _mergeVariantArtifactsIntoRows(rows) {
  if (!Array.isArray(rows)) return rows;
  return rows.map((row) => {
    const sessionId = row?.session_id || '';
    const overlay = sessionId ? variantArtifactOverlay.get(sessionId) : null;
    if (!overlay) return row;
    row.variant_artifacts = { ...(row.variant_artifacts || {}), ...overlay };
    return row;
  });
}

function hydrateVariantArtifactOverlay(index) {
  if (!index) return;
  index.active_rows = _mergeVariantArtifactsIntoRows(index.active_rows || []);
  index.inactive_rows = _mergeVariantArtifactsIntoRows(index.inactive_rows || []);
  index.rows = _mergeVariantArtifactsIntoRows(index.rows || []);
}

function rememberVariantArtifact(data) {
  const artifact = data?.variant_artifact ? { ...data.variant_artifact } : null;
  const sessionId = artifact?.session_id || data?.session_id || '';
  const variant = artifact?.variant || data?.variant || '';
  if (!artifact || !sessionId || !variant) return;
  const uiSourceWindow = normalizeTraceSourceWindow(
    data?.ui_source_window
      || data?.requested_source_window
      || artifact.ui_source_window
      || artifact.requested_source_window
      || artifact.window_anchor?.ui_source_window
      || data?.source_window
      || artifact.source_window
      || '',
  );
  artifact.path = artifact.path || artifactPathFromCapture(data);
  artifact.artifact_path = artifact.artifact_path || artifact.path;
  artifact.source_clip_path = artifact.source_clip_path || sourceClipPathFromCapture(data);
  artifact.clip_path = artifact.clip_path || artifact.source_clip_path;
  artifact.session_id = artifact.session_id || sessionId;
  artifact.variant = artifact.variant || variant;
  artifact.ui_source_window = uiSourceWindow;
  const current = variantArtifactOverlay.get(sessionId) || {};
  current[variant] = artifact;
  if (artifact.identity_key) {
    const byIdentity = current.by_source_identity || {};
    const identityVariants = byIdentity[artifact.identity_key] || {};
    identityVariants[variant] = artifact;
    byIdentity[artifact.identity_key] = identityVariants;
    current.by_source_identity = byIdentity;
  }
  const identityKey = traceVariantIdentityKeyFromArtifact(artifact, variant, uiSourceWindow);
  if (identityKey) {
    const byIdentity = current.by_source_identity || {};
    const identityVariants = byIdentity[identityKey] || {};
    identityVariants[variant] = artifact;
    byIdentity[identityKey] = identityVariants;
    current.by_source_identity = byIdentity;
  }
  variantArtifactOverlay.set(sessionId, current);
  if (missionIndex) hydrateVariantArtifactOverlay(missionIndex);
}

function normalizeTraceSourceWindow(sourceWindow) {
  const value = String(sourceWindow || '').trim();
  if ([SOURCE_WINDOW_PROMPT_CYCLE, SOURCE_WINDOW_SELECTED_TURN, SOURCE_WINDOW_FULL_THREAD, SOURCE_WINDOW_FULL_THREAD_CONCISE].includes(value)) return value;
  return DEFAULT_TRACE_SOURCE_WINDOW;
}

function backendTraceSourceWindow(sourceWindow) {
  const value = normalizeTraceSourceWindow(sourceWindow);
  return value === SOURCE_WINDOW_FULL_THREAD_CONCISE ? SOURCE_WINDOW_FULL_THREAD : value;
}

function traceVariantIdentityKeyFromArtifact(artifact, variant, sourceWindow) {
  if (!artifact) return '';
  const sessionId = artifact.session_id || '';
  if (!sessionId || !variant) return '';
  const promptSha16 = artifact.prompt_sha16 || artifact.window_anchor?.prompt_sha16 || 'noprompt';
  const turnRaw = artifact.turn_index ?? artifact.window_anchor?.turn_index ?? null;
  const turn = turnRaw != null && Number.isFinite(Number(turnRaw)) ? Number(turnRaw) : 'noturn';
  return `session=${sessionId}|window=${normalizeTraceSourceWindow(sourceWindow)}|prompt=${promptSha16 || 'noprompt'}|turn=${turn}|variant=${variant || ''}`;
}

function tracePrimaryVariantForSource(sourceWindow) {
  return normalizeTraceSourceWindow(sourceWindow) === SOURCE_WINDOW_FULL_THREAD_CONCISE
    ? 'closeout_report'
    : 'trace_capsule';
}

function tracePrimaryVariantLabel(variant, sourceWindow) {
  if (variant === 'closeout_report' && normalizeTraceSourceWindow(sourceWindow) === SOURCE_WINDOW_FULL_THREAD_CONCISE) return 'thread compact';
  if (variant === 'closeout_report') return 'closeout';
  return 'trace capsule';
}

function selectedTraceSourceWindow() {
  const normalized = normalizeTraceSourceWindow(dropdownEls?.missionSourceWindow?.value || window.__aiwTraceSourceWindow || DEFAULT_TRACE_SOURCE_WINDOW);
  const value = normalized === SOURCE_WINDOW_SELECTED_TURN ? DEFAULT_TRACE_SOURCE_WINDOW : normalized;
  window.__aiwTraceSourceWindow = value;
  if (dropdownEls?.missionSourceWindow && dropdownEls.missionSourceWindow.value !== value) {
    dropdownEls.missionSourceWindow.value = value;
  }
  return value;
}

function objectOrEmpty(value) {
  return value && typeof value === 'object' && !Array.isArray(value) ? value : {};
}

function loadMissionOperatorMarkers() {
  try {
    const parsed = JSON.parse(window.localStorage?.getItem(MISSION_OPERATOR_MARKER_STORAGE_KEY) || '{}');
    if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) return parsed;
  } catch (_) {}
  return {};
}

function persistMissionOperatorMarkers() {
  try {
    window.localStorage?.setItem(MISSION_OPERATOR_MARKER_STORAGE_KEY, JSON.stringify(missionOperatorMarkers));
  } catch (_) {}
}

function missionOperatorMarker(rowOrKey) {
  const key = typeof rowOrKey === 'string' ? rowOrKey : missionKey(rowOrKey);
  const rowMarker = typeof rowOrKey === 'string' ? {} : objectOrEmpty(rowOrKey?.operator_marker);
  const marker = objectOrEmpty(missionOperatorMarkers?.[key]);
  const nativeMarkers = objectOrEmpty(missionIndex?.operator_markers);
  return { ...objectOrEmpty(nativeMarkers?.[key]), ...rowMarker, ...marker };
}

function setMissionOperatorMarker(rowOrKey, patch = {}) {
  const key = typeof rowOrKey === 'string' ? rowOrKey : missionKey(rowOrKey);
  if (!key) return null;
  const existing = missionOperatorMarker(key);
  const next = {
    ...existing,
    ...objectOrEmpty(patch),
    schema_version: 'agent_trace_operator_marker_v1',
    mission_key: key,
    updated_at_ms: Date.now(),
  };
  if (patch.clear === true) {
    delete missionOperatorMarkers[key];
  } else {
    missionOperatorMarkers[key] = next;
  }
  persistMissionOperatorMarkers();
  postNative('setMissionOperatorMarker', patch.clear === true ? { mission_key: key, clear: true } : next);
  return missionOperatorMarker(key);
}

function markerDueState(marker = {}, now = Date.now()) {
  const dueAt = _numberOrNull(marker.follow_up_due_at_ms);
  if (!dueAt) return { due: false, label: '' };
  const delta = dueAt - now;
  if (delta <= 0) return { due: true, label: 'follow-up due now' };
  const minutes = Math.ceil(delta / 60000);
  if (minutes < 60) return { due: false, label: `follow-up due in ${minutes}m` };
  return { due: false, label: `follow-up due in ${Math.ceil(minutes / 60)}h` };
}

function traceSourceWindowConfig(sourceWindow) {
  const value = normalizeTraceSourceWindow(sourceWindow);
  if (value === SOURCE_WINDOW_FULL_THREAD) {
    return {
      label: 'full thread detailed',
      actionLabel: 'Full Thread Detailed',
      receiptLabel: 'full thread detailed',
      optionLabel: 'Full thread detailed',
      definition: 'all turns with app-visible thinking plus command/output trace',
      intendedUse: 'dense debug archive; largest copy',
      description: 'all turns in this Claude/Codex session with visible thinking and detailed trace context',
    };
  }
  if (value === SOURCE_WINDOW_FULL_THREAD_CONCISE) {
    return {
      label: 'full thread compact',
      actionLabel: 'Thread Compact',
      receiptLabel: 'full thread compact',
      optionLabel: 'Full thread compact',
      definition: 'closeouts, app-visible thinking trace, changed files, command stats',
      intendedUse: 'thread handoff without raw tool bodies',
      description: 'compact whole-thread closeout and app-visible thinking trace',
    };
  }
  if (value === SOURCE_WINDOW_SELECTED_TURN) {
    return {
      label: 'single turn',
      actionLabel: 'Single Turn',
      receiptLabel: 'single turn',
      optionLabel: 'Single turn',
      definition: 'one backend turn',
      intendedUse: 'internal backend identity',
      description: 'one backend turn',
    };
  }
  return {
    label: 'latest response bundle',
    actionLabel: 'Response Bundle',
    receiptLabel: 'latest response bundle',
    optionLabel: 'Latest response bundle',
    definition: 'saved latest-response capsule with app-visible thinking, tool context, bounded source excerpts, and source shard/projection refs',
    intendedUse: 'default copy; closeout included when available',
    description: 'the selected response, prompt, visible thinking, tool context, and prompt-file/read-output excerpts when available',
  };
}

function traceSourceWindowLabel(sourceWindow) {
  return traceSourceWindowConfig(sourceWindow).label;
}

function traceSourceWindowActionLabel(sourceWindow) {
  return traceSourceWindowConfig(sourceWindow).actionLabel;
}

function traceWindowForSource(row, sourceWindow, displayTurn = null) {
  const lct = displayTurn || (rowHasActiveTrace(row) ? activityDisplayTurn(row) : traceDisplayTurn(row));
  const value = normalizeTraceSourceWindow(sourceWindow);
  if (backendTraceSourceWindow(value) === SOURCE_WINDOW_FULL_THREAD) return objectOrEmpty(lct.full_thread_trace_window);
  if (value === SOURCE_WINDOW_SELECTED_TURN) return {};
  return objectOrEmpty(lct.trace_window);
}

function traceSourceWindowRangeLabel(row, sourceWindow, displayTurn = null) {
  const turn = displayTurn || (rowHasActiveTrace(row) ? activityDisplayTurn(row) : traceDisplayTurn(row));
  const value = normalizeTraceSourceWindow(sourceWindow);
  const traceWindow = traceWindowForSource(row, value, turn);
  const knownThreadCount = missionKnownThreadTurnCount(row, turn);
  const knownLatestTurn = missionKnownLatestTurnIndex(row, turn);
  const fullBackend = backendTraceSourceWindow(value) === SOURCE_WINDOW_FULL_THREAD;
  if (value === SOURCE_WINDOW_SELECTED_TURN) {
    return turn?.turn_index != null ? `turn #${turn.turn_index} only` : 'one backend turn';
  }
  const start = traceWindow.start_turn_index ?? (fullBackend && knownThreadCount > 1 ? 1 : turn?.turn_index) ?? null;
  const end = traceWindow.end_turn_index ?? (fullBackend ? knownLatestTurn : turn?.turn_index) ?? null;
  const count = Math.max(
    1,
    _numberOrNull(traceWindow.turn_count) || 0,
    fullBackend ? knownThreadCount : (_numberOrNull(turn?.trace_window_turn_count) || 0),
  );
  if (start != null && end != null && Number.isFinite(count) && count > 1) return `turns #${start}-${end}`;
  if (end != null) return `turn #${end}`;
  return traceSourceWindowConfig(value).description;
}

function _numberOrNull(value) {
  const n = Number(value);
  return Number.isFinite(n) ? n : null;
}

function providerLabel(provider) {
  if (provider === 'claude_code' || provider === 'claude') return 'Claude Code';
  if (provider === 'codex') return 'Codex';
  return provider ? String(provider).replace(/_/g, ' ') : 'Unknown provider';
}

function providerShortBadge(provider) {
  if (provider === 'claude_code' || provider === 'claude') return 'Claude';
  if (provider === 'codex') return 'Codex';
  return '?';
}

function shortSessionId(sessionId) {
  const raw = String(sessionId || '');
  if (!raw) return 'no-session-id';
  if (raw.length <= 14) return raw;
  return `${raw.slice(0, 8)}…${raw.slice(-4)}`;
}

function missionKnownThreadTurnCount(row, displayTurn = null) {
  const sourceFreshness = objectOrEmpty(row?.source_freshness);
  const turn = displayTurn || row?.preferred_trace_turn || row?.latest_completed_turn || row?.stale_active_turn || row?.active_turn || {};
  return Math.max(
    1,
    _numberOrNull(sourceFreshness.current_turn_count)
      || _numberOrNull(row?.turn_count_hint)
      || _numberOrNull(row?.completed_turn_count)
      || _numberOrNull(row?.completed_turns_hint)
      || _numberOrNull(turn?.full_thread_trace_window?.turn_count)
      || _numberOrNull(turn?.full_thread_turn_count)
      || _numberOrNull(turn?.turn_index)
      || 1,
  );
}

function missionKnownLatestTurnIndex(row, displayTurn = null) {
  const sourceFreshness = objectOrEmpty(row?.source_freshness);
  const turn = displayTurn || row?.preferred_trace_turn || row?.latest_completed_turn || row?.stale_active_turn || row?.active_turn || {};
  return Math.max(
    1,
    _numberOrNull(sourceFreshness.current_latest_turn_index)
      || _numberOrNull(row?.latest_turn_index)
      || _numberOrNull(turn?.full_thread_trace_window?.end_turn_index)
      || _numberOrNull(turn?.turn_index)
      || missionKnownThreadTurnCount(row, turn),
  );
}

function missionFullThreadAvailable(row, displayTurn = null) {
  return missionKnownThreadTurnCount(row, displayTurn) > 1;
}

function traceVariantEstimate(row, variant, sourceWindow, displayTurn = null) {
  if (!row) return null;
  const identity = selectedSourceIdentity(row, variant, sourceWindow);
  const measured = identity.identity_key ? missionSizeMeasurements.get(identity.identity_key) : null;
  const measuredBytes = _numberOrNull(measured?.bytes);
  if (measuredBytes && measuredBytes > 0) {
    return {
      bytes: measuredBytes,
      exact: true,
      source: measured.source || 'native_current_measure',
      sha16: measured.sha16 || '',
      sourceWindow: identity.source_window,
      measuredAt: measured.measuredAt || 0,
    };
  }
  const turn = displayTurn || (rowHasActiveTrace(row) ? activityDisplayTurn(row) : traceDisplayTurn(row));
  const estimates = turn?.trace_variant_size_estimates || {};
  const byVariant = estimates?.[variant] || {};
  const backendWindow = backendTraceSourceWindow(sourceWindow);
  const estimate = byVariant?.[backendWindow] || byVariant?.[normalizeTraceSourceWindow(sourceWindow)] || null;
  const bytes = _numberOrNull(estimate?.bytes);
  if (!bytes || bytes <= 0) return null;
  const cacheState = String(row?.trace_summary_cache_state || turn?.cache_state || '').toLowerCase();
  const staleSummary = cacheState.includes('stale');
  return {
    bytes,
    exact: estimate.exact !== false && !staleSummary,
    source: staleSummary ? 'stale_renderer_measurement' : (estimate.source || estimates.status || 'renderer_estimate'),
    sha16: estimate.sha16 || '',
    sourceWindow: backendWindow,
  };
}

function heuristicTraceArtifactBytes(row, sourceWindow, displayTurn = null) {
  const value = normalizeTraceSourceWindow(sourceWindow);
  const turn = displayTurn || (rowHasActiveTrace(row) ? activityDisplayTurn(row) : traceDisplayTurn(row));
  const traceWindow = traceWindowForSource(row, value, turn);
  const knownThreadCount = missionKnownThreadTurnCount(row, turn);
  const fullBackend = backendTraceSourceWindow(value) === SOURCE_WINDOW_FULL_THREAD;
  const fullTurnCount = Math.max(
    1,
    knownThreadCount
      || _numberOrNull(turn?.full_thread_turn_count)
      || _numberOrNull(row?.completed_turns_hint)
      || _numberOrNull(row?.turn_count_hint)
      || _numberOrNull(turn?.turn_index)
      || 1,
  );
  const turnCount = value === SOURCE_WINDOW_SELECTED_TURN
    ? 1
    : Math.max(1, _numberOrNull(traceWindow.turn_count) || 0, fullBackend ? knownThreadCount : (_numberOrNull(turn?.trace_window_turn_count) || 0));
  const toolCount = _numberOrNull(traceWindow.tool_count)
    || _numberOrNull(fullBackend ? turn?.full_thread_tool_count : turn?.trace_window_tool_count)
    || _numberOrNull(turn?.tool_count)
    || 0;
  const rawBytes = Math.max(0, _numberOrNull(row?.size_bytes) || 0);
  if (!rawBytes) return 0;
  if (value === SOURCE_WINDOW_FULL_THREAD) return Math.max(4096, Math.round(rawBytes * 0.28));
  if (value === SOURCE_WINDOW_FULL_THREAD_CONCISE) return Math.max(4096, Math.round(2400 + turnCount * 900 + toolCount * 120));
  const ratio = Math.min(1, Math.max(1, turnCount) / fullTurnCount);
  return Math.max(2048, Math.round(rawBytes * ratio * 0.18));
}

function traceScopeMetrics(row, sourceWindow, displayTurn = null) {
  const value = normalizeTraceSourceWindow(sourceWindow);
  const turn = displayTurn || (rowHasActiveTrace(row) ? activityDisplayTurn(row) : traceDisplayTurn(row));
  const traceWindow = traceWindowForSource(row, value, turn);
  const config = traceSourceWindowConfig(value);
  const knownThreadCount = missionKnownThreadTurnCount(row, turn);
  const fullBackend = backendTraceSourceWindow(value) === SOURCE_WINDOW_FULL_THREAD;
  const fullTurnCount = Math.max(
    1,
    knownThreadCount
      || _numberOrNull(turn?.full_thread_turn_count)
      || _numberOrNull(row?.completed_turns_hint)
      || _numberOrNull(row?.turn_count_hint)
      || _numberOrNull(turn?.turn_index)
      || 1,
  );
  const turnCount = value === SOURCE_WINDOW_SELECTED_TURN
    ? 1
    : Math.max(1, _numberOrNull(traceWindow.turn_count) || 0, fullBackend ? knownThreadCount : (_numberOrNull(turn?.trace_window_turn_count) || 0));
  const rawBytes = Math.max(0, _numberOrNull(row?.size_bytes) || 0);
  const primaryVariant = tracePrimaryVariantForSource(value);
  const rendererEstimate = traceVariantEstimate(row, primaryVariant, value, turn);
  const estimatedBytes = rendererEstimate?.bytes || heuristicTraceArtifactBytes(row, value, turn);
  const toolCount = value === SOURCE_WINDOW_SELECTED_TURN
    ? _numberOrNull(turn?.tool_count)
    : (_numberOrNull(traceWindow.tool_count)
      || _numberOrNull(fullBackend ? turn?.full_thread_tool_count : turn?.trace_window_tool_count)
      || _numberOrNull(turn?.tool_count));
  const errorCount = value === SOURCE_WINDOW_SELECTED_TURN
    ? _numberOrNull(turn?.error_count)
    : (_numberOrNull(traceWindow.error_count)
      || _numberOrNull(fullBackend ? turn?.full_thread_error_count : turn?.trace_window_error_count)
      || _numberOrNull(turn?.error_count));
  return {
    sourceWindow: value,
    label: config.optionLabel || config.actionLabel,
    definition: config.definition || config.description,
    intendedUse: config.intendedUse || '',
    range: traceSourceWindowRangeLabel(row, value, turn),
    turnCount,
    fullTurnCount,
    toolCount,
    errorCount,
    estimatedBytes,
    estimateExact: Boolean(rendererEstimate?.exact),
    estimateSource: rendererEstimate?.source || 'heuristic',
    primaryVariant,
    byteLabel: estimatedBytes ? `${rendererEstimate?.exact ? '' : '~'}${_formatKB(estimatedBytes)}` : 'size unknown',
    rawByteLabel: rawBytes ? _formatKB(rawBytes) : 'raw size unknown',
    large: estimatedBytes >= TRACE_SCOPE_LARGE_BYTES || (value === SOURCE_WINDOW_FULL_THREAD && rawBytes >= TRACE_SCOPE_LARGE_BYTES),
  };
}

function traceCapsuleCopySize(row, sourceWindow, displayTurn = null) {
  if (!row) return { bytes: 0, label: 'copy size unknown', exact: false, ready: false };
  const value = normalizeTraceSourceWindow(sourceWindow);
  const variant = tracePrimaryVariantForSource(value);
  const artifact = variantArtifact(row, variant, value);
  const currentness = variantArtifactCurrentness(row, artifact, variant, value);
  const label = tracePrimaryVariantLabel(variant, value);
  if (artifact?.bytes && currentness.ready) {
    return { bytes: Number(artifact.bytes) || 0, label: `${label} ${_formatKB(artifact.bytes)}`, exact: true, ready: true, variant };
  }
  const rendererEstimate = traceVariantEstimate(row, variant, value, displayTurn);
  if (rendererEstimate?.bytes) {
    const prefix = rendererEstimate.exact ? label : `last ${label}`;
    return { bytes: rendererEstimate.bytes, label: `${prefix} ${_formatKB(rendererEstimate.bytes)}`, exact: rendererEstimate.exact, ready: false, variant };
  }
  const metrics = traceScopeMetrics(row, value, displayTurn);
  if (metrics.estimatedBytes) {
    return { bytes: metrics.estimatedBytes, label: `${label} est. ${metrics.byteLabel}`, exact: false, ready: false, variant };
  }
  if (artifact?.bytes) {
    return { bytes: Number(artifact.bytes) || 0, label: `last ${label} ${_formatKB(artifact.bytes)}`, exact: false, ready: false, variant };
  }
  return { bytes: 0, label: `${label} size after prepare`, exact: false, ready: false, variant };
}

function traceThreadTotality(sourceWindow) {
  const value = normalizeTraceSourceWindow(sourceWindow);
  if (value === SOURCE_WINDOW_FULL_THREAD) return 'full_thread_detailed';
  if (value === SOURCE_WINDOW_FULL_THREAD_CONCISE) return 'full_thread_compact';
  if (value === SOURCE_WINDOW_SELECTED_TURN) return 'selected_turn_only';
  return 'latest_response_bundle_only';
}

function missionRuntimeState(row, displayTurn, view) {
  if (!row) return 'none';
  const activeTrace = rowHasActiveTrace(row);
  if (activeTrace && !rowHasStaleActiveTurn(row)) return 'running_active_turn';
  if (view?.activity === 'checking') return 'checking_stale_active_cache';
  if (view?.activity === 'retired') return 'retired';
  if (displayTurn?.turn_index == null) return 'no_turn';
  return 'finished_selected_turn';
}

function missionArtifactState(row, sourceWindow, view) {
  if (!row) return 'missing';
  if (view?.copy === 'just_copied') return 'copied';
  if (view?.copy === 'pending_after_copy') return 'copied_waiting_for_followup';
  if (view?.copy === 'copying') return 'copying';
  if (view?.copy === 'copy_failed') return 'copy_failed';
  const variant = tracePrimaryVariantForSource(sourceWindow);
  const artifact = variantArtifact(row, variant, sourceWindow);
  const currentness = artifact ? variantArtifactCurrentness(row, artifact, variant, sourceWindow) : null;
  if (artifact?.path && currentness?.ready) return 'ready_current';
  if (artifact?.path && currentness?.source_freshness?.action === 'block_copy') return 'blocked_stale_artifact';
  if (artifact?.path && currentness?.source_freshness?.action === 'refresh_before_copy') return 'stale_refresh_required';
  if (artifact?.path) return 'stale_or_mismatched';
  return 'not_materialized';
}

function missionHasGoalMode(row, counts = {}) {
  const goal = missionGoal(row);
  return Boolean(
    row?.has_goal
      || goal?.goal_id
      || row?.goal_status
      || counts.goal_rollup_status === 'captured_goal_mode'
      || counts.goal_status === 'captured_goal_mode'
      || counts.mode_state === 'goal_mode_marked'
      || counts.mode_lifecycle_state === 'goal_mode_marked'
  );
}

function missionNoEditGoalSoftGate(row, counts = {}) {
  const substrate = canonicalDiffState(counts.substrate_diff || counts.diff_state);
  return missionHasGoalMode(row, counts)
    && Number(counts.edit_path_count || 0) === 0
    && Number(counts.ui_diff_count || 0) === 0
    && (counts.commit_diff_missing === true || substrate === 'commit_diff_missing');
}

function missionHasSubstrateDiffEvidence(counts = {}) {
  const substrate = canonicalDiffState(counts.substrate_diff || counts.diff_state);
  const editCount = _numberOrNull(counts.edit_path_count ?? counts.edit_count) ?? 0;
  const uiDiffCount = _numberOrNull(counts.ui_diff_count ?? counts.visible_ui_diff_count) ?? 0;
  const commitCount = _numberOrNull(counts.commit_count) ?? 0;
  return editCount > 0
    || uiDiffCount > 0
    || commitCount > 0
    || counts.commit_diff_missing === true
    || substrate === 'commit_diff_missing'
    || counts.thread_total_edits === 'has_edit_or_commit_evidence';
}

function missionDiffState(row, sourceWindow) {
  const variant = tracePrimaryVariantForSource(sourceWindow);
  const artifact = variantArtifact(row, variant, sourceWindow);
  const counts = artifactTraceCounts(artifact);
  if (!artifact?.path) return 'not_materialized';
  if (normalizeTraceSourceWindow(sourceWindow) === SOURCE_WINDOW_FULL_THREAD_CONCISE) return 'compact_summary_only';
  const currentness = variantArtifactCurrentness(row, artifact, variant, sourceWindow);
  const hasDiffEvidence = missionHasSubstrateDiffEvidence(counts);
  if (counts.substrate_diff === 'exact_hunks_attached') return currentness?.ready ? 'exact_plus_minus_attached' : 'stale_exact_plus_minus_attached';
  if (counts.substrate_diff === 'ui_summary_only') return currentness?.ready ? 'ui_summary_only' : 'stale_ui_summary_only';
  if (missionNoEditGoalSoftGate(row, counts)) return 'goal_no_edits_captured_in_scope';
  if (counts.commit_diff_missing === true) return 'commit_diff_missing';
  if (counts.substrate_diff === 'commit_diff_missing') return 'commit_diff_missing';
  if (hasDiffEvidence && (counts.substrate_diff === 'missing_exact_plus_minus' || counts.substrate_diff_required === true)) return 'missing_exact_plus_minus';
  if (Number(counts.edit_path_count || 0) === 0) return counts.no_edit_claim_allowed === true ? 'no_edits_proven_for_scope' : 'no_edits_captured_in_scope';
  return 'missing_exact_plus_minus';
}

function missionRowVisibilityState(row) {
  if (!row) return 'unknown';
  if (rowIsOldPrefixRetired(row) || row?.inactive_reason === 'archived' || row?.retirement?.retired_cause) return 'archived';
  if (inactiveMissionRows().some((item) => missionKey(item) === missionKey(row))) return showInactiveMissions ? 'old' : 'hidden_by_filter';
  return 'recent';
}

function missionInterventionScope(counts, row, sourceWindow) {
  const source = objectOrEmpty(row?.operator_interventions || counts.operator_interventions);
  const selected = _numberOrNull(source.selected_window_count ?? counts.operator_intervention_selected_window_count ?? counts.operator_intervention_count);
  const fullRaw = _numberOrNull(source.full_thread_count ?? counts.operator_intervention_full_thread_count);
  const fullThreadAvailable = source.full_thread_available != null
    ? boolish(source.full_thread_available)
    : (counts.full_thread_available != null ? boolish(counts.full_thread_available) : missionFullThreadAvailable(row));
  const selectedOnly = normalizeTraceSourceWindow(sourceWindow) !== SOURCE_WINDOW_FULL_THREAD;
  const full = selectedOnly ? fullRaw : (fullRaw ?? selected ?? 0);
  const outside = _numberOrNull(source.outside_selected_window_count ?? (full != null && selected != null ? Math.max(0, full - selected) : null));
  return {
    schema_version: 'agent_trace_operator_interventions_scoped_v1',
    selected_window_count: selected ?? 0,
    full_thread_count: fullThreadAvailable ? full : null,
    outside_selected_window_count: outside,
    full_thread_available: fullThreadAvailable,
    scope_note: selectedOnly
      ? 'selected/latest copy scope; zero means selected window only unless full_thread_count is known'
      : 'full-thread copy scope',
    rows: Array.isArray(source.rows) ? source.rows : [],
  };
}

function artifactStatsSource(row, artifact, sourceWindow, contract = null) {
  const identity = contract?.identity || selectedSourceIdentity(row, tracePrimaryVariantForSource(sourceWindow), sourceWindow);
  const turn = artifact?.turn_index ?? contract?.capsule_turn_index ?? null;
  const selectedTurn = identity.turn_index ?? null;
  const window = artifact?.source_window || contract?.capsule_source_window || normalizeTraceSourceWindow(sourceWindow);
  const sha = artifact?.source_sha16 || contract?.capsule_source_sha16 || artifact?.sha16 || '';
  const label = artifact?.path
    ? `capsule turn #${turn ?? 'unknown'} for ${window}${sha ? ` sha ${String(sha).slice(0, 8)}` : ''}`
    : `not materialized for selected turn #${selectedTurn ?? 'unknown'}`;
  return {
    schema_version: 'agent_trace_artifact_stats_source_v1',
    label,
    artifact_turn_index: turn,
    selected_turn_index: selectedTurn,
    artifact_source_window: window,
    selected_source_window: identity.source_window,
    artifact_sha16: sha,
    matches_selected_turn: selectedTurn == null || turn == null ? null : Number(turn) === Number(selectedTurn),
  };
}

function missionCopyPolicy(row, selectedSourceWindow, counts = {}, scope = null) {
  const value = normalizeTraceSourceWindow(selectedSourceWindow);
  const metrics = scope || traceScopeMetrics(row, value);
  const fullThreadAvailable = missionFullThreadAvailable(row) || Number(metrics.fullTurnCount || 0) > 1 || boolish(counts.full_thread_available);
  const fullDetailed = traceScopeMetrics(row, SOURCE_WINDOW_FULL_THREAD);
  const traceBudget = VARIANT_SIZE_BUDGETS.trace_capsule || Infinity;
  const fullFits = fullDetailed.estimatedBytes > 0 && fullDetailed.estimatedBytes <= traceBudget;
  const latestOnly = value === DEFAULT_TRACE_SOURCE_WINDOW || value === SOURCE_WINDOW_SELECTED_TURN;
  const consumer = promptShelfConsumerForSlot(promptShelfLastCopiedSlot) || 'type_b_continue';
  const planImplRisk = String(counts.mode_state || counts.mode_lifecycle_state || '').includes('plan_plus')
    || (latestOnly && fullThreadAvailable && Number(metrics.turnCount || 0) <= 1);
  const typeBFullConsumers = ['type_b_continue', 'type_b_semantic_carryforward', 'type_b_visual_refinement'];
  const recommendedScope = consumer === 'compact'
    ? SOURCE_WINDOW_FULL_THREAD_CONCISE
    : (typeBFullConsumers.includes(consumer) && fullThreadAvailable && fullFits ? SOURCE_WINDOW_FULL_THREAD : value);
  return {
    schema_version: 'agent_trace_copy_policy_v1',
    consumer,
    recommended_scope: recommendedScope,
    selected_scope: value,
    full_thread_available: fullThreadAvailable,
    full_thread_fits_budget: fullFits,
    risk_if_latest_only: latestOnly && fullThreadAvailable
      ? (planImplRisk ? 'plan/implementation episodes may be outside copied scope' : 'full thread exists but selected scope is latest only')
      : '',
    header_warning: latestOnly ? 'LATEST ONLY - not full thread' : '',
  };
}

function missionVariantRoster(row, selectedSourceWindow = selectedTraceSourceWindow(), displayTurn = null) {
  const turn = displayTurn || (rowHasActiveTrace(row) ? activityDisplayTurn(row) : traceDisplayTurn(row));
  const stale = isSourceIndexStale(row) || traceSummaryCacheState(row).includes('stale');
  const roster = TRACE_OPERATOR_SOURCE_WINDOWS.map((value) => {
    const metrics = traceScopeMetrics(row, value, turn);
    const copySize = traceCapsuleCopySize(row, value, turn);
    return {
      source_window: value,
      selected: normalizeTraceSourceWindow(selectedSourceWindow) === value,
      label: metrics.label,
      variant: copySize.variant || tracePrimaryVariantForSource(value),
      turn_range: metrics.range,
      turn_count: metrics.turnCount,
      full_thread_turn_count: metrics.fullTurnCount,
      bytes: copySize.bytes || metrics.estimatedBytes || 0,
      size_label: copySize.label || metrics.byteLabel,
      exact: Boolean(copySize.exact),
      materialized: Boolean(copySize.ready),
      estimate_source: metrics.estimateSource,
      coverage_state: stale ? 'source_index_refresh_required' : 'current_or_estimable',
    };
  });
  const latest = roster.find((entry) => entry.source_window === DEFAULT_TRACE_SOURCE_WINDOW);
  const full = roster.find((entry) => entry.source_window === SOURCE_WINDOW_FULL_THREAD);
  if (latest && full && full.turn_count > latest.turn_count && latest.bytes > 0 && latest.bytes === full.bytes && stale) {
    latest.coverage_state = 'stale_parity_suspicious';
    full.coverage_state = 'stale_parity_suspicious';
  }
  return roster;
}

function missionWorkbenchHealth(row, roster, sourceContract) {
  const reasons = [];
  const stale = isSourceIndexStale(row) || traceSummaryCacheState(row).includes('stale');
  if (stale) reasons.push('source_index_stale_or_cached_summary_stale');
  if (sourceContract?.action && sourceContract.action !== 'allow_copy') reasons.push(sourceContract.action);
  if ((roster || []).some((entry) => entry.coverage_state === 'stale_parity_suspicious')) reasons.push('latest_and_full_size_parity_from_stale_summary');
  const state = sourceContract?.action === 'block_copy'
    ? 'blocked'
    : (reasons.length ? 'refresh_required' : 'ok');
  return {
    schema_version: 'agent_trace_workbench_health_v1',
    state,
    reasons,
    refresh_required: state !== 'ok',
    copy_allowed_without_refresh: state === 'ok',
  };
}

function missionInstallSingletonEvidence() {
  const freshness = resourceFreshnessPayload();
  const rows = Array.isArray(freshness.rows) ? freshness.rows : [];
  const runtimeRows = rows.filter((row) => row?.blocking !== false);
  const appRow = rows.find((row) => row?.path === 'app.mjs') || runtimeRows[0] || rows[0] || {};
  const mismatches = Array.isArray(freshness.blocking_mismatches)
    ? freshness.blocking_mismatches
    : (Array.isArray(freshness.mismatches) ? freshness.mismatches.filter((row) => row?.blocking !== false) : []);
  return {
    schema_version: 'agent_trace_install_singleton_v1',
    status: freshness.status || 'unknown',
    ok: freshness.ok === true,
    repo_root: freshness.repo_root || '',
    bundle_resource_url: freshness.bundle_resource_url || '',
    repo_resource_sha256: appRow.repo_sha256 || '',
    installed_resource_sha256: appRow.bundle_sha256 || appRow.installed_sha256 || '',
    running_resource_sha256: appRow.bundle_sha256 || appRow.installed_sha256 || '',
    checked_at: freshness.checked_at || '',
    stale_instance_detected: isResourceBundleStale(),
    mismatch_count: Number(freshness.blocking_mismatch_count ?? freshness.mismatch_count ?? mismatches.length ?? 0) || 0,
    stale_instance_action: isResourceBundleStale()
      ? 'reinstall_or_reload_before_trusting_trace_workbench_evidence'
      : 'none',
    rows: runtimeRows.slice(0, 12).map((row) => ({
      kind: row.kind || '',
      path: row.path || '',
      ok: row.ok === true,
      repo_sha256: row.repo_sha256 || '',
      installed_sha256: row.bundle_sha256 || row.installed_sha256 || '',
      blocking: row.blocking !== false,
    })),
    mismatches: mismatches.slice(0, 12).map((row) => ({
      kind: row.kind || '',
      path: row.path || '',
      repo_sha256: row.repo_sha256 || '',
      installed_sha256: row.bundle_sha256 || row.installed_sha256 || '',
      blocking: row.blocking !== false,
    })),
  };
}

function missionGoalRollup(row, displayTurn, counts = {}) {
  const goal = missionGoal(row) || {};
  const status = missionGoalStatus(row) || (goal.goal_id ? 'unknown_goal' : 'none');
  const passes = [];
  const goalPassCount = _numberOrNull(counts.goal_pass_count ?? counts.goal_passes);
  if (goalPassCount && goalPassCount > 0) {
    passes.push({
      kind: 'goal_passes_from_artifact',
      count: goalPassCount,
      scope: 'copied_artifact',
    });
  }
  if (row?.has_goal || goal.goal_id || row?.goal_status) {
    passes.push({
      kind: 'goal_authority_row',
      goal_id: goal.goal_id || '',
      status,
      objective_preview: goal.objective_preview || row?.current_telos || '',
    });
  }
  if (displayTurn?.turn_index != null) {
    passes.push({
      kind: traceTurnLooksActive(displayTurn) ? 'active_turn' : 'completed_turn',
      turn_index: displayTurn.turn_index,
      status: traceTurnLooksActive(displayTurn) ? 'active' : 'complete',
    });
  }
  return {
    schema_version: 'agent_trace_goal_rollup_v1',
    status,
    goal_id: goal.goal_id || '',
    objective_preview: goal.objective_preview || row?.current_telos || '',
    token_budget: goal.token_budget ?? null,
    tokens_used: goal.tokens_used ?? null,
    pass_count: passes.length,
    passes,
    durable_scope: 'mission_row_plus_artifact_counts',
  };
}

function missionDiffReconciler(row, artifact, counts, sourceWindow, sourceContract, scope) {
  const value = normalizeTraceSourceWindow(sourceWindow);
  const diffState = missionDiffState(row, value);
  const substrate = canonicalDiffState(counts.substrate_diff || counts.diff_state || diffState);
  const editCount = _numberOrNull(counts.edit_path_count) ?? 0;
  const uiDiffCount = _numberOrNull(counts.ui_diff_count) ?? 0;
  const commitCount = _numberOrNull(counts.commit_count) ?? 0;
  const hasCommitEvidence = commitCount > 0 || counts.commit_diff_missing === true || substrate === 'commit_diff_missing';
  const fullThreadCompact = value === SOURCE_WINDOW_FULL_THREAD_CONCISE;
  const hasExactHunks = substrate === 'exact_hunks_attached' || diffState === 'exact_plus_minus_attached' || diffState === 'stale_exact_plus_minus_attached';
  const uiOnly = uiDiffCount > 0 || substrate === 'ui_summary_only' || diffState === 'ui_summary_only' || diffState === 'stale_ui_summary_only';
  const commitWithoutPatch = counts.commit_diff_missing === true || substrate === 'commit_diff_missing' || diffState === 'commit_diff_missing';
  const substrateEvidencePresent = editCount > 0
    || uiDiffCount > 0
    || hasCommitEvidence
    || counts.thread_total_edits === 'has_edit_or_commit_evidence';
  const noEditGoalSoftGate = commitWithoutPatch
    && editCount === 0
    && !uiOnly
    && missionHasGoalMode(row, counts);
  // substrate_diff_required is a conditional contract, not standalone proof
  // that a zero-edit capsule is missing a diff.
  const exactRequired = !noEditGoalSoftGate && !fullThreadCompact && substrateEvidencePresent;
  const reasons = [];
  let status = 'unknown';
  let severity = 'amber';
  if (fullThreadCompact) {
    status = 'summary_only_allowed';
    severity = 'green';
    reasons.push('full_thread_concise_summary_exception');
  } else if (hasExactHunks) {
    status = 'aligned_exact_substrate_diff';
    severity = 'green';
  } else if (noEditGoalSoftGate) {
    status = 'goal_no_edits_captured_commit_observation_only';
    severity = 'amber';
    reasons.push('goal_mode_zero_edit_commit_observation_not_copy_blocker');
  } else if (commitWithoutPatch) {
    status = 'commit_without_exact_diff';
    severity = 'red';
    reasons.push('commit_seen_without_git_show_patch');
  } else if (uiOnly) {
    status = 'ui_diff_only_missing_substrate_hunks';
    severity = 'red';
    reasons.push('ui_review_card_is_not_substrate_diff');
  } else if (exactRequired) {
    status = 'missing_exact_substrate_diff';
    severity = 'red';
    reasons.push('edit_or_commit_evidence_requires_plus_minus_hunks');
  } else if (editCount === 0 && counts.no_edit_claim_allowed === true) {
    status = 'no_edits_proven_for_full_thread_scope';
    severity = 'green';
  } else if (editCount === 0) {
    status = 'no_edits_captured_in_scoped_window';
    severity = 'amber';
    reasons.push('zero_edit_count_is_window_local');
  }
  const unqualifiedNoEditsAllowed = counts.no_edit_claim_allowed === true
    && value === SOURCE_WINDOW_FULL_THREAD
    && !hasCommitEvidence
    && editCount === 0;
  return {
    schema_version: 'agent_trace_diff_reconciler_v1',
    status,
    severity,
    reasons,
    source_window: value,
    thread_totality: traceThreadTotality(value),
    exact_diff_required: exactRequired,
    full_thread_compact_summary_exception: fullThreadCompact,
    copied_capsule: {
      path: artifact?.path || '',
      schema_version: artifact?.schema_version || '',
      source_window: artifact?.source_window || '',
      currentness_action: sourceContract?.action || 'unknown',
      source_sha16: artifact?.source_sha16 || '',
    },
    ui_review_card: {
      state: uiOnly ? 'present_without_substrate_hunks' : 'not_detected',
      ui_diff_count: uiDiffCount,
    },
    parser_artifact_delta: {
      state: hasExactHunks ? 'exact_hunks_attached' : (substrate || 'not_detected'),
      edit_path_count: editCount,
      substrate_diff: substrate || '',
      substrate_diff_required: exactRequired,
      no_edit_claim_allowed: counts.no_edit_claim_allowed === true,
    },
    git_commit_or_worktree: {
      state: hasCommitEvidence
        ? (commitWithoutPatch ? (noEditGoalSoftGate ? 'commit_observed_without_patch' : 'commit_seen_without_patch') : 'commit_seen')
        : 'not_detected',
      commit_count: commitCount,
      commit_diff_missing: commitWithoutPatch && !noEditGoalSoftGate,
      commit_observation_softened: noEditGoalSoftGate,
    },
    scope: {
      turns_covered: scope?.turnCount ?? null,
      full_thread_turn_count: scope?.fullTurnCount ?? null,
      selected_window_only: value === DEFAULT_TRACE_SOURCE_WINDOW || value === SOURCE_WINDOW_SELECTED_TURN,
    },
    edit_claim: {
      edits: editCount,
      edits_zero_scope: editCount === 0 ? traceThreadTotality(value) : '',
      unqualified_no_edits_allowed: unqualifiedNoEditsAllowed,
      type_b_phrase: unqualifiedNoEditsAllowed
        ? 'no edits were made in the covered full thread'
        : 'no edits captured in this source window',
    },
  };
}

function missionEvidenceTier(row, artifact, sourceWindow, sourceContract) {
  const value = normalizeTraceSourceWindow(sourceWindow);
  const hasProviderSource = Boolean(row?.session_file || row?.source_path || row?.session_path || sourceContract?.source_sha16);
  const copiedSourceReconstructable = Boolean(artifact?.path || row?.latest_completed_turn || row?.preferred_trace_turn || row?.active_turn);
  return {
    schema_version: 'agent_trace_evidence_tier_v1',
    selected_tier: artifact?.path ? 'tier_1_trace_capsule_projection' : 'tier_4_catalog_row_before_materialization',
    provider_forensic_available: hasProviderSource,
    provider_byte_lossless: false,
    visible_clip_lossless_for_copied_source: copiedSourceReconstructable,
    copied_source_reconstructable: copiedSourceReconstructable,
    source_window: value,
    source_truth_boundary: 'visible workbench evidence is copied-source-lossless; provider byte losslessness requires raw provider source',
    retrievable_in: hasProviderSource ? ['local_provider_source', 'trace_capsule_artifact'] : ['trace_capsule_artifact'],
  };
}

function missionTerminalValidationEvidence(counts, artifact) {
  const terminalCount = _numberOrNull(counts.terminal_validation_count) ?? 0;
  const terminalPass = _numberOrNull(counts.terminal_validation_pass_count) ?? 0;
  const terminalFail = _numberOrNull(counts.terminal_validation_fail_count) ?? 0;
  const validationCount = _numberOrNull(counts.validation_count) ?? 0;
  const state = terminalFail > 0
    ? 'terminal_failures_present'
    : (terminalPass > 0 ? 'terminal_pass_present' : (validationCount > 0 ? 'non_terminal_validation_only' : 'not_captured'));
  return {
    schema_version: 'agent_trace_terminal_validation_v1',
    state,
    terminal_validation_count: terminalCount,
    terminal_pass_count: terminalPass,
    terminal_fail_count: terminalFail,
    validation_count: validationCount,
    priority_rule: 'terminal owner-scope validation outranks ambient historical command status',
    source: artifact?.path ? 'artifact_trace_counts' : 'catalog_row_only',
  };
}

function missionAgentEpisodeGraph(row, sourceWindow, displayTurn, artifact, counts, interventions, diffReconciler, goalRollup, terminalValidation) {
  const value = normalizeTraceSourceWindow(sourceWindow);
  const events = [];
  const push = (kind, payload = {}) => {
    events.push({
      id: `e${String(events.length + 1).padStart(3, '0')}`,
      kind,
      ...payload,
    });
  };
  push('turn_selected', {
    turn_index: displayTurn?.turn_index ?? null,
    source_window: value,
    thread_totality: traceThreadTotality(value),
  });
  if (goalRollup.status !== 'none') {
    for (const pass of goalRollup.passes || []) push('goal_pass', pass);
  }
  const interventionRows = Array.isArray(interventions.rows) ? interventions.rows : [];
  for (const rowEntry of interventionRows.slice(0, 20)) {
    push('operator_intervention', {
      source_window: value,
      exact_excerpt: rowEntry.exact_excerpt || rowEntry.excerpt || rowEntry.text || '',
      line_range: rowEntry.line_range || null,
      event_scope: rowEntry.scope || 'captured_source',
    });
  }
  const editCount = _numberOrNull(counts.edit_path_count) ?? 0;
  const commitCount = _numberOrNull(counts.commit_count) ?? 0;
  const validationCount = _numberOrNull(counts.validation_count) ?? 0;
  if (editCount > 0 || diffReconciler.git_commit_or_worktree.state !== 'not_detected') {
    push('implementation_episode', {
      edit_path_count: editCount,
      diff_status: diffReconciler.status,
      exact_diff_required: diffReconciler.exact_diff_required,
    });
  }
  if (commitCount > 0 || diffReconciler.git_commit_or_worktree.commit_diff_missing) {
    push('commit_evidence', {
      commit_count: commitCount,
      commit_diff_missing: diffReconciler.git_commit_or_worktree.commit_diff_missing,
    });
  }
  if (validationCount > 0 || terminalValidation.terminal_validation_count > 0) {
    push('validation_episode', {
      validation_count: validationCount,
      terminal_state: terminalValidation.state,
    });
  }
  push('copy_artifact', {
    artifact_path: artifact?.path || '',
    artifact_state: artifact?.path ? 'materialized_or_cached' : 'not_materialized',
    source_window: value,
  });
  if (counts.closeout_present === true) push('closeout_evidence', { state: 'present' });
  return {
    schema_version: 'agent_episode_graph_v1',
    composition_root: 'agent_episode_graph',
    provider_thread: {
      provider: row?.provider || '',
      session_id: row?.session_id || '',
      mission_key: missionKey(row),
      title: missionDisplayTitle(row, displayTurn),
      selected_turn_index: displayTurn?.turn_index ?? null,
      selected_source_window: value,
      full_thread_turn_count: missionKnownThreadTurnCount(row, displayTurn),
    },
    nodes: events,
    events,
    artifacts: [
      {
        kind: 'trace_capsule',
        path: artifact?.path || '',
        source_window: artifact?.source_window || value,
        schema_version: artifact?.schema_version || '',
      },
    ],
    invariants: {
      edits_zero_always_scoped: true,
      exact_diff_required_unless_full_thread_compact: !diffReconciler.full_thread_compact_summary_exception,
      provider_bytes_not_claimed_lossless: true,
    },
    counts: {
      command_count: _numberOrNull(counts.command_count) ?? 0,
      edit_path_count: editCount,
      validation_count: validationCount,
      operator_intervention_selected_window_count: interventions.selected_window_count ?? 0,
      operator_intervention_full_thread_count: interventions.full_thread_count ?? null,
    },
  };
}

function missionTypeBHandoffLint(copyPolicy, sourceContract, diffReconciler, evidenceTier) {
  const blockers = [];
  const warnings = [];
  if (sourceContract?.action === 'block_copy') blockers.push('source_or_artifact_blocked');
  if (sourceContract?.action === 'refresh_before_copy') warnings.push('refresh_before_copy_required');
  if (copyPolicy?.header_warning) warnings.push('selected_window_only');
  if (copyPolicy?.risk_if_latest_only) warnings.push('full_thread_recommended_for_type_b');
  if (diffReconciler.severity === 'red') blockers.push(diffReconciler.status);
  if (diffReconciler.severity === 'amber') warnings.push(diffReconciler.status);
  if (!evidenceTier.provider_forensic_available) warnings.push('provider_forensic_source_not_attached');
  return {
    schema_version: 'agent_trace_type_b_handoff_lint_v1',
    result: blockers.length ? 'block' : (warnings.length ? 'warn' : 'pass'),
    blockers,
    warnings,
    no_edits_sentence_allowed: diffReconciler.edit_claim.unqualified_no_edits_allowed === true,
    required_no_edit_language: diffReconciler.edit_claim.unqualified_no_edits_allowed
      ? 'no edits were made in the covered full thread'
      : 'no edits captured in this source window',
    refusal_rule: 'refuse unqualified "no edits were made" unless full-thread coverage and no-edit evidence prove it',
    prohibited_when_false: ['no files were edited', 'no edits were made', 'nothing changed'],
  };
}

function missionCopyReadinessGate(sourceContract, copyPolicy, diffReconciler, evidenceTier, typeBLint, installSingleton, artifact) {
  const blockers = [];
  const warnings = [];
  if (sourceContract?.action === 'block_copy') blockers.push(sourceContract.mismatch_reason || 'source_blocked');
  if (typeBLint.blockers?.length) blockers.push(...typeBLint.blockers);
  if (sourceContract?.action === 'refresh_before_copy') warnings.push(sourceContract.mismatch_reason || 'refresh_before_copy');
  if (!artifact?.path) warnings.push('prepare_or_capture_needed');
  if (copyPolicy?.header_warning) warnings.push(copyPolicy.header_warning);
  if (copyPolicy?.risk_if_latest_only) warnings.push(copyPolicy.risk_if_latest_only);
  if (diffReconciler.severity === 'amber') warnings.push(diffReconciler.status);
  if (!evidenceTier.provider_forensic_available) warnings.push('provider_forensic_source_not_attached');
  if (installSingleton.stale_instance_detected) warnings.push('installed_app_bundle_stale');
  const state = blockers.length ? 'red' : (warnings.length ? 'amber' : 'green');
  return {
    schema_version: 'agent_trace_copy_readiness_gate_v1',
    state,
    normal_copy_allowed: state !== 'red',
    must_refresh_before_trusting: sourceContract?.action === 'refresh_before_copy' || installSingleton.stale_instance_detected,
    blockers,
    warnings,
    copy_action: state === 'red'
      ? 'block_and_show_why'
      : (sourceContract?.action === 'refresh_before_copy' ? 'refresh_then_copy' : (artifact?.path ? 'copy_current_artifact' : 'prepare_then_copy')),
    type_b_no_edits_claim_allowed: typeBLint.no_edits_sentence_allowed,
    required_type_b_no_edit_language: typeBLint.required_no_edit_language,
  };
}

function missionAttentionLaneLabel(lane) {
  return (MISSION_ATTENTION_LANES.find(([key]) => key === lane) || [lane, String(lane || 'Mission')])[1];
}

function missionReviewAgeDecay(ageMs) {
  // Capped so red rows stay above the 8600 soft-review tier; only gives
  // fresh-first ordering when several blockers stack in the lane.
  return Math.min(700, Math.round(Math.log1p(Math.max(0, ageMs) / 3_600_000) * 120));
}

function missionAttentionModel(row, pieces = {}, renderStart = Date.now()) {
  const view = pieces.view || missionViewStateForRow(row, renderStart);
  const displayTurn = pieces.displayTurn || (rowHasActiveTrace(row) ? activityDisplayTurn(row) : traceDisplayTurn(row));
  const sourceWindow = normalizeTraceSourceWindow(pieces.sourceWindow || selectedTraceSourceWindow());
  const marker = missionOperatorMarker(row);
  const copyReadiness = pieces.copyReadiness || {};
  const diffReconciler = pieces.diffReconciler || {};
  const sourceContract = pieces.sourceContract || {};
  const copyPolicy = pieces.copyPolicy || {};
  const workbenchHealth = pieces.workbenchHealth || {};
  const goalRollup = pieces.goalRollup || {};
  const artifact = pieces.artifact || null;
  const reasons = [];
  const rogueReasons = [];
  const markerDue = markerDueState(marker, renderStart);
  const lifecycleState = view.retired ? 'retired'
    : view.activity === 'live' ? 'running'
    : view.activity === 'checking' ? 'checking'
    : view.activity === 'waiting' ? 'waiting'
    : view.activity === 'copied' ? 'copied'
    : ['just_finished', 'recent', 'warm', 'idle'].includes(view.activity) ? 'finished'
    : view.activity || 'unknown';
  const runtimeState = pieces.runtimeState || missionRuntimeState(row, displayTurn, view);
  const goalState = missionGoalStatus(row) || (missionGoal(row) ? 'unknown_goal' : 'none');
  const copyState = view.copy || 'none';
  const rowVisibilityState = missionRowVisibilityState(row);
  const fullThreadAvailable = missionFullThreadAvailable(row, displayTurn);
  const waitingKind = copyState === 'pending_after_copy'
    ? 'type_b_response_expected'
    : (view.activity === 'checking'
      ? 'stale_source_verification'
      : (goalRollup.status === 'blocked' ? 'dependency_blocked' : 'none'));
  const handoffState = copyState === 'pending_after_copy'
    ? 'copied_awaiting_type_b_response'
    : (copyState === 'just_copied'
      ? 'copied_waiting_paste'
      : (copyState === 'copy_failed'
        ? 'copy_failed'
        : (artifact?.path ? 'prepared_not_copied' : 'not_copied')));
  const reviewState = marker.reviewed_at_ms
    ? 'operator_reviewed'
    : (copyState === 'pending_after_copy'
      ? 'handoff_sent_waiting'
      : (copyReadiness.state === 'red' || diffReconciler.severity === 'red' || workbenchHealth.state === 'refresh_required'
        ? 'needs_review'
        : (['just_finished', 'recent'].includes(view.activity) ? 'needs_review' : 'no_review_needed')));
  const freshnessState = sourceContract?.action === 'block_copy'
    ? 'blocked'
    : (sourceContract?.action === 'refresh_before_copy'
      ? 'refresh_required'
      : (sourceContract?.ready ? 'current' : (sourceContract?.source_index_state || sourceFreshnessState(row) || 'unknown')));
  let riskState = 'green';
  if (copyReadiness.state === 'red' || diffReconciler.severity === 'red' || sourceContract?.action === 'block_copy') riskState = 'red';
  else if (copyReadiness.state === 'amber' || diffReconciler.severity === 'amber' || sourceContract?.action === 'refresh_before_copy' || copyPolicy.risk_if_latest_only) riskState = 'amber';
  if (rowHasStaleActiveTurn(row) && !rowHasActiveGoal(row)) rogueReasons.push('stale active turn cache');
  if (view.activity === 'checking' && sourceContract?.action === 'refresh_before_copy') rogueReasons.push('source changed while row still appears open');
  if (runtimeState === 'running_active_turn' && sourceContract?.source_index_state && sourceContract.source_index_state !== 'current') rogueReasons.push('running row has non-current source index');
  if (marker.pinned) reasons.push('operator pinned');
  if (marker.snoozed_until_ms && Number(marker.snoozed_until_ms) > renderStart) reasons.push('operator snoozed');
  if (markerDue.due) reasons.push(markerDue.label);
  if (copyReadiness.state === 'red') reasons.push(`copy readiness red: ${(copyReadiness.blockers || []).slice(0, 2).join(', ') || 'blocked'}`);
  if (copyReadiness.state === 'amber') reasons.push(`copy readiness amber: ${(copyReadiness.warnings || []).slice(0, 2).join(', ') || 'scope/freshness caveat'}`);
  if (diffReconciler.status && diffReconciler.status !== 'no_artifact') reasons.push(`diff ${String(diffReconciler.status).replace(/_/g, ' ')}`);
  if (copyPolicy.risk_if_latest_only) reasons.push(copyPolicy.risk_if_latest_only);
  if (workbenchHealth.state && workbenchHealth.state !== 'ok') reasons.push(`workbench ${String(workbenchHealth.state).replace(/_/g, ' ')}`);
  if (rogueReasons.length) reasons.push(...rogueReasons.map((reason) => `rogue active check: ${reason}`));
  if (!reasons.length && view.activity === 'live') reasons.push('running background mission');
  if (!reasons.length && view.activity === 'just_finished') reasons.push('recently finished and ready for review');

  const sourceHardBlocked = sourceContract?.action === 'block_copy';
  const reviewAgeMs = Math.max(0, renderStart - (_missionSortTime(row) || renderStart));
  const reviewFresh = reviewAgeMs <= MISSION_REVIEW_FRESH_MS;
  // Top review lane = genuine "now": a hard source block, OR a fresh blocker/finish
  // the operator has not cleared. Aged soft-quality reds and operator-reviewed rows
  // drop to Older/Finished so Needs Review Now keeps its label (the row stays
  // risk-tinted and copy-blocked — only its lane/score change).
  const redNeedsReview = riskState === 'red' && (sourceHardBlocked || (reviewFresh && !marker.reviewed_at_ms));
  const softNeedsReview = !marker.reviewed_at_ms && reviewFresh && (markerDue.due || reviewState === 'needs_review');
  let attentionState = 'older_finished_copied';
  let lane = 'older_finished_copied';
  let score = 100;
  const archivedWithoutRevival = rowVisibilityState === 'archived' && view.copy === 'none' && !['copied', 'waiting', 'live', 'just_finished'].includes(view.activity);
  if (marker.retired || view.retired || archivedWithoutRevival) {
    attentionState = 'retired';
    lane = 'retired';
    score = -1000;
  } else if (marker.snoozed_until_ms && Number(marker.snoozed_until_ms) > renderStart) {
    attentionState = 'snoozed';
    lane = 'paused_deferred';
    score = marker.pinned ? 6500 : 300;
  } else if (redNeedsReview) {
    attentionState = 'review_now';
    lane = 'needs_review_now';
    score = 9900 - missionReviewAgeDecay(reviewAgeMs);
  } else if (softNeedsReview) {
    attentionState = 'review_now';
    lane = 'needs_review_now';
    score = 8600;
  } else if (copyState === 'pending_after_copy') {
    attentionState = 'copied_waiting_response';
    lane = 'waiting_on_operator';
    score = 6200;
  } else if (copyState === 'just_copied') {
    attentionState = 'copied_waiting_paste';
    lane = 'waiting_on_operator';
    score = 5800;
  } else if (copyReadiness.state !== 'red' && ['just_finished', 'recent', 'warm'].includes(view.activity) && displayTurn?.turn_index != null) {
    attentionState = 'copy_ready';
    lane = 'ready_to_copy';
    score = fullThreadAvailable ? 7200 : 6600;
  } else if (rogueReasons.length) {
    attentionState = 'rogue_active';
    lane = 'rogue_active';
    score = 5600;
  } else if (view.activity === 'live') {
    attentionState = 'running_background';
    lane = 'running_background_goals';
    score = 4200;
  } else if (view.activity === 'checking') {
    attentionState = 'rogue_active';
    lane = 'rogue_active';
    score = 5400;
  } else if (view.activity === 'idle') {
    attentionState = 'paused_or_deferred';
    lane = 'paused_deferred';
    score = 900;
  }
  if (riskState === 'amber') score += 900;
  if (marker.pinned) score += 5000;
  if (markerDue.due) score += 3000;
  if (copyPolicy.recommended_scope && copyPolicy.selected_scope && copyPolicy.recommended_scope !== copyPolicy.selected_scope) score += 700;
  score += Math.min(500, Math.max(0, _missionSortTime(row) / 100000000000));
  return {
    schema_version: 'agent_trace_mission_attention_v1',
    lifecycle_state: lifecycleState,
    view_activity: view.activity,
    goal_state: goalState,
    runtime_state: runtimeState,
    handoff_state: handoffState,
    review_state: reviewState,
    copy_state: copyState,
    freshness_state: freshnessState,
    risk_state: riskState,
    waiting_kind: waitingKind,
    attention_state: attentionState,
    attention_score: Math.round(score),
    attention_reasons: reasons.slice(0, 8),
    lane,
    lane_label: missionAttentionLaneLabel(lane),
    rogue_active_reasons: rogueReasons,
    operator_marker: marker,
    follow_up_due: markerDue,
  };
}

function beginMissionAttentionMemo() {
  missionAttentionMemo = new Map();
  missionAttentionMemoActive = true;
}

function endMissionAttentionMemo() {
  missionAttentionMemoActive = false;
  missionAttentionMemo = new Map();
}

function missionAttentionForRow(row, renderStart = Date.now(), sourceWindow = selectedTraceSourceWindow()) {
  if (missionAttentionMemoActive) {
    const memoKey = `${missionKey(row)}|${normalizeTraceSourceWindow(sourceWindow)}`;
    const hit = missionAttentionMemo.get(memoKey);
    if (hit) return hit;
    const computed = missionStateModel(row, sourceWindow, renderStart).mission_attention || missionAttentionModel(row, {}, renderStart);
    missionAttentionMemo.set(memoKey, computed);
    return computed;
  }
  return missionStateModel(row, sourceWindow, renderStart).mission_attention || missionAttentionModel(row, {}, renderStart);
}

function missionWhyThisRow(row, stateModelPieces) {
  const { displayTurn, sourceContract, workbenchHealth, copyReadiness, diffReconciler, goalRollup } = stateModelPieces;
  return {
    schema_version: 'agent_trace_why_this_row_v1',
    selected_because: [
      rowHasActiveTrace(row) ? 'active_trace_turn_present' : 'latest_completed_or_cached_trace_turn',
      missionGoal(row) ? 'goal_thread_present' : '',
      workbenchHealth.state !== 'ok' ? 'trace_workbench_attention_required' : '',
    ].filter(Boolean),
    title: missionDisplayTitle(row, displayTurn),
    turn_index: displayTurn?.turn_index ?? null,
    source_freshness_action: sourceContract?.action || 'unknown',
    copy_readiness: copyReadiness.state,
    diff_reconciler_status: diffReconciler.status,
    goal_status: goalRollup.status,
  };
}

function missionWhyThisCopy(row, stateModelPieces) {
  const { sourceWindow, scope, sourceContract, copyPolicy, copyReadiness, diffReconciler, evidenceTier } = stateModelPieces;
  const value = normalizeTraceSourceWindow(sourceWindow);
  return {
    schema_version: 'agent_trace_why_this_copy_v1',
    selected_scope: value,
    recommended_scope: copyPolicy.recommended_scope,
    range: scope.range,
    turns_covered: scope.turnCount,
    full_thread_turn_count: scope.fullTurnCount,
    source_action: sourceContract?.action || 'unknown',
    readiness_state: copyReadiness.state,
    diff_status: diffReconciler.status,
    evidence_tier: evidenceTier.selected_tier,
    warning: copyPolicy.risk_if_latest_only || copyPolicy.header_warning || '',
    row_key: missionKey(row),
  };
}

function missionStateModel(row, sourceWindow = selectedTraceSourceWindow(), renderStart = Date.now()) {
  const displayTurn = rowHasActiveTrace(row) ? activityDisplayTurn(row) : traceDisplayTurn(row);
  const view = missionViewStateForRow(row, renderStart);
  const scope = traceScopeMetrics(row, sourceWindow, displayTurn);
  const variant = tracePrimaryVariantForSource(sourceWindow);
  const artifact = variantArtifact(row, variant, sourceWindow);
  const currentness = artifact ? variantArtifactCurrentness(row, artifact, variant, sourceWindow) : variantArtifactCurrentness(row, artifact, variant, sourceWindow);
  const counts = artifactTraceCounts(artifact);
  const copyEntry = view?.copyEntry || {};
  const interventions = missionInterventionScope(counts, row, sourceWindow);
  const copyPolicy = missionCopyPolicy(row, sourceWindow, counts, scope);
  const sourceContract = currentness?.source_freshness || sourceFreshnessContract(row, artifact, variant, sourceWindow);
  const variantRoster = missionVariantRoster(row, sourceWindow, displayTurn);
  const workbenchHealth = missionWorkbenchHealth(row, variantRoster, sourceContract);
  const diffReconciler = missionDiffReconciler(row, artifact, counts, sourceWindow, sourceContract, scope);
  const evidenceTier = missionEvidenceTier(row, artifact, sourceWindow, sourceContract);
  const terminalValidation = missionTerminalValidationEvidence(counts, artifact);
  const goalRollup = missionGoalRollup(row, displayTurn, counts);
  const agentEpisodeGraph = missionAgentEpisodeGraph(row, sourceWindow, displayTurn, artifact, counts, interventions, diffReconciler, goalRollup, terminalValidation);
  const installSingleton = missionInstallSingletonEvidence();
  const typeBLint = missionTypeBHandoffLint(copyPolicy, sourceContract, diffReconciler, evidenceTier);
  const copyReadiness = missionCopyReadinessGate(sourceContract, copyPolicy, diffReconciler, evidenceTier, typeBLint, installSingleton, artifact);
  const commonPieces = {
    view,
    artifact,
    displayTurn,
    sourceWindow,
    scope,
    sourceContract,
    copyPolicy,
    workbenchHealth,
    copyReadiness,
    diffReconciler,
    evidenceTier,
    goalRollup,
    runtimeState: missionRuntimeState(row, displayTurn, view),
  };
  const attention = missionAttentionModel(row, commonPieces, renderStart);
  return {
    runtime_state: commonPieces.runtimeState,
    goal_state: missionGoalStatus(row) || (missionGoal(row) ? 'unknown_goal' : 'none'),
    mission_attention: attention,
    mode_state: counts.mode_state || counts.mode_lifecycle_state || 'unknown',
    artifact_state: missionArtifactState(row, sourceWindow, view),
    row_visibility_state: missionRowVisibilityState(row),
    copy_scope: normalizeTraceSourceWindow(sourceWindow),
    copy_scope_label: traceSourceWindowConfig(sourceWindow).optionLabel || traceSourceWindowLabel(sourceWindow),
    thread_totality: traceThreadTotality(sourceWindow),
    diff_state: missionDiffState(row, sourceWindow),
    freshness_state: sourceContract.source_index_state || sourceFreshnessState(row) || row?.artifact_freshness?.state || 'unknown',
    source_freshness: sourceContract,
    source_freshness_action: sourceContract.action,
    source_latest_fallback_available: traceCopyCanUseSourceLatestFallback(row, sourceWindow, rowHasActiveTrace(row), { source_freshness: sourceContract }),
    stats_source: artifactStatsSource(row, artifact, sourceWindow, sourceContract),
    copy_policy: copyPolicy,
    copy_readiness: copyReadiness,
    diff_reconciler: diffReconciler,
    agent_episode_graph: agentEpisodeGraph,
    goal_rollup: goalRollup,
    evidence_tier: evidenceTier,
    type_b_handoff_lint: typeBLint,
    terminal_validation: terminalValidation,
    install_singleton: installSingleton,
    why_this_row: missionWhyThisRow(row, commonPieces),
    why_this_copy: missionWhyThisCopy(row, commonPieces),
    variant_roster: variantRoster,
    workbench_health: workbenchHealth,
    turns_covered: scope.turnCount,
    thread_turn_count: missionKnownThreadTurnCount(row, displayTurn),
    full_thread_available: missionFullThreadAvailable(row, displayTurn) || normalizeTraceSourceWindow(sourceWindow) === SOURCE_WINDOW_FULL_THREAD,
    intervention_count: interventions.selected_window_count ?? interventions.full_thread_count ?? 0,
    operator_interventions: interventions,
    closeout_state: counts.closeout_present === true ? 'present' : 'not_captured',
    last_copied_scope: copyEntry.copiedSourceWindowLabel || '',
    copy_state: view?.copy || 'none',
  };
}

function missionStateModelText(model) {
  if (!model) return '';
  const bits = [
    `runtime ${String(model.runtime_state).replace(/_/g, ' ')}`,
    model.mission_attention?.lane_label ? `lane ${model.mission_attention.lane_label}` : '',
    model.mission_attention?.risk_state ? `risk ${model.mission_attention.risk_state}` : '',
    model.mission_attention?.waiting_kind && model.mission_attention.waiting_kind !== 'none' ? `waiting ${model.mission_attention.waiting_kind.replace(/_/g, ' ')}` : '',
    `goal ${String(model.goal_state).replace(/_/g, ' ')}`,
    `mode ${String(model.mode_state).replace(/_/g, ' ')}`,
    `artifact ${String(model.artifact_state).replace(/_/g, ' ')}`,
    `row ${String(model.row_visibility_state || 'unknown').replace(/_/g, ' ')}`,
    `diff ${String(model.diff_state).replace(/_/g, ' ')}`,
    `diff gate ${String(model.diff_reconciler?.status || 'unknown').replace(/_/g, ' ')}`,
    `readiness ${String(model.copy_readiness?.state || 'unknown').replace(/_/g, ' ')}`,
    `type b ${String(model.type_b_handoff_lint?.result || 'unknown').replace(/_/g, ' ')}`,
    `scope ${model.copy_scope_label}`,
    `totality ${String(model.thread_totality).replace(/_/g, ' ')}`,
    `${model.turns_covered} turn${model.turns_covered === 1 ? '' : 's'}`,
    `thread ${model.thread_turn_count || model.turns_covered} turn${(model.thread_turn_count || model.turns_covered) === 1 ? '' : 's'}`,
    model.full_thread_available ? 'full thread available' : 'full thread not proven',
    `health ${String(model.workbench_health?.state || 'unknown').replace(/_/g, ' ')}`,
    `copy ${String(model.source_freshness_action || 'unknown').replace(/_/g, ' ')}`,
    `stats ${model.stats_source?.label || 'unknown source'}`,
    `interventions selected=${model.operator_interventions?.selected_window_count ?? 'unknown'} full=${model.operator_interventions?.full_thread_count ?? 'unknown'}`,
    `closeout ${String(model.closeout_state).replace(/_/g, ' ')}`,
    `evidence ${String(model.evidence_tier?.selected_tier || 'unknown').replace(/_/g, ' ')}`,
    model.last_copied_scope ? `last copied ${model.last_copied_scope}` : '',
  ];
  return bits.filter(Boolean).join(' · ');
}

function closeoutReportSize(row, sourceWindow) {
  const backendWindow = backendTraceSourceWindow(sourceWindow);
  const artifact = variantArtifact(row, 'closeout_report', backendWindow);
  const currentness = artifact ? variantArtifactCurrentness(row, artifact, 'closeout_report', backendWindow) : null;
  if (artifact?.bytes && currentness?.ready) return `closeout ${_formatKB(artifact.bytes)}`;
  const estimate = traceVariantEstimate(row, 'closeout_report', backendWindow);
  if (estimate?.bytes) return `${estimate.exact ? 'closeout' : 'last closeout'} ${_formatKB(estimate.bytes)}`;
  if (artifact?.bytes) return `last closeout ${_formatKB(artifact.bytes)}`;
  return 'closeout included if present';
}

function sourceFreshnessOperatorText(row, flabel = null) {
  if (isLiveSourceUpdating(row)) return 'live source changing';
  if (isSourceIndexStale(row)) return sourceFreshnessState(row).replace(/_/g, ' ') || 'source index stale';
  if (flabel?.text) return flabel.text.toLowerCase();
  return 'current enough to copy';
}

function selectedMissionOperatorSentence(row, sourceWindow = selectedTraceSourceWindow()) {
  if (!row) return 'Select a mission thread to prepare a Trace Capsule.';
  const displayTurn = rowHasActiveTrace(row) ? activityDisplayTurn(row) : traceDisplayTurn(row);
  const activeTrace = rowHasActiveTrace(row);
  const fresh = (row.artifact_freshness || {}).state || 'unknown';
  const reason = (row.artifact_freshness || {}).reason || '';
  const flabel = _freshLabel(fresh, reason, displayTurn.turn_index != null, sourceFreshnessState(row), activeTrace);
  const scope = traceScopeMetrics(row, sourceWindow, displayTurn);
  const copySize = traceCapsuleCopySize(row, sourceWindow, displayTurn);
  const stateModel = missionStateModel(row, sourceWindow);
  const copyPolicy = stateModel.copy_policy || {};
  const sourceAction = stateModel.source_freshness_action ? `copy action ${stateModel.source_freshness_action.replace(/_/g, ' ')}` : '';
  const turnText = displayTurn.turn_index != null
    ? `${activeTrace ? 'active' : 'latest'} turn #${displayTurn.turn_index}`
    : 'no turn';
  const title = missionDisplayTitle(row, displayTurn);
  const large = scope.large ? ' · large/slow' : '';
  const errors = scope.errorCount ? `, ${scope.errorCount} errors` : '';
  const tools = scope.toolCount != null ? `, ${scope.toolCount} tools` : '';
  const goal = missionGoalOperatorText(row);
  const subagents = missionSubagentOperatorText(row);
  return [
    `${title}`,
    `${providerLabel(row.provider)} · ${turnText} · runtime ${stateModel.runtime_state.replace(/_/g, ' ')} · goal ${stateModel.goal_state.replace(/_/g, ' ')} · ${sourceFreshnessOperatorText(row, flabel)}`,
    goal,
    missionStateModelText(stateModel),
    copyPolicy.risk_if_latest_only || copyPolicy.header_warning || '',
    sourceAction,
    `${scope.label}: ${scope.range}, ${scope.turnCount} turn${scope.turnCount === 1 ? '' : 's'}${tools}${errors}`,
    `${copySize.label}; ${closeoutReportSize(row, sourceWindow)}; app-visible thinking/progress included when present${large}.`,
    subagents,
  ].filter(Boolean).join(' · ');
}

// One-line chip for the visible Selected-mission row above the Trace Capsule
// card. The full operator sentence above still feeds the legacy
// #selected-mission surface; this keeps only the scannable identity + state.
function selectedMissionOperatorChip(row, sourceWindow = selectedTraceSourceWindow()) {
  if (!row) return 'Select a mission thread to prepare a Trace Capsule.';
  const displayTurn = rowHasActiveTrace(row) ? activityDisplayTurn(row) : traceDisplayTurn(row);
  const activeTrace = rowHasActiveTrace(row);
  const stateModel = missionStateModel(row, sourceWindow);
  const turnText = displayTurn.turn_index != null
    ? `${activeTrace ? 'active' : 'latest'} turn #${displayTurn.turn_index}`
    : 'no turn';
  return [
    missionDisplayTitle(row, displayTurn),
    providerLabel(row.provider),
    turnText,
    `runtime ${String(stateModel.runtime_state).replace(/_/g, ' ')}`,
    stateModel.goal_state && stateModel.goal_state !== 'none'
      ? `goal ${String(stateModel.goal_state).replace(/_/g, ' ')}`
      : '',
    stateModel.mission_attention?.lane_label || '',
  ].filter(Boolean).join(' · ');
}

// Copy-success flash for the selected scope row. Driven by a module-level flash
// record (not a one-shot DOM class) so the polling re-render of the scope rows
// preserves the green state, plus a negative animation-delay so a mid-flash
// re-render resumes the keyframes at the right point instead of restarting the
// pop. Lives only in the left trace pane, clear of the mission list.
const SCOPE_COPY_FLASH_MS = 7000;
let __scopeCopyFlash = { window: null, start: 0 };
let __scopeCopyFlashTimer = null;

function decorateScopeRowCopyFlash(div, value, now) {
  const active = __scopeCopyFlash.window === value
    && (now - __scopeCopyFlash.start) < SCOPE_COPY_FLASH_MS;
  if (active) {
    div.dataset.copied = 'true';
    div.style.animationDelay = `${-(now - __scopeCopyFlash.start)}ms`;
  } else {
    div.dataset.copied = 'false';
    div.style.animationDelay = '';
  }
}

function flashScopeCopySuccess(sourceWindow) {
  const value = sourceWindow || selectedTraceSourceWindow();
  if (!value) return;
  __scopeCopyFlash = { window: value, start: Date.now() };
  const el = dropdownEls?.missionScopeContract;
  if (el) {
    const now = Date.now();
    for (const div of el.querySelectorAll('.scope-contract-row')) {
      decorateScopeRowCopyFlash(div, div.dataset.sourceWindow, now);
    }
  }
  if (__scopeCopyFlashTimer) window.clearTimeout(__scopeCopyFlashTimer);
  __scopeCopyFlashTimer = window.setTimeout(() => {
    __scopeCopyFlash = { window: null, start: 0 };
    __scopeCopyFlashTimer = null;
    const el2 = dropdownEls?.missionScopeContract;
    if (!el2) return;
    for (const div of el2.querySelectorAll('.scope-contract-row')) {
      div.dataset.copied = 'false';
      div.style.animationDelay = '';
    }
  }, SCOPE_COPY_FLASH_MS);
}

function renderMissionScopeContract(row, selectedSourceWindow = selectedTraceSourceWindow()) {
  const el = dropdownEls?.missionScopeContract;
  if (!el) return;
  el.replaceChildren();
  const options = TRACE_OPERATOR_SOURCE_WINDOWS;
  if (!row) {
    const empty = document.createElement('div');
    empty.className = 'scope-contract-empty';
    empty.textContent = 'Select a mission to estimate scope size.';
    el.appendChild(empty);
    return;
  }
  const displayTurn = rowHasActiveTrace(row) ? activityDisplayTurn(row) : traceDisplayTurn(row);
  for (const value of options) {
    const metrics = traceScopeMetrics(row, value, displayTurn);
    const copySize = traceCapsuleCopySize(row, value, displayTurn);
    const closeoutSize = closeoutReportSize(row, value);
    const div = document.createElement('button');
    div.type = 'button';
    div.className = 'scope-contract-row';
    div.dataset.sourceWindow = value;
    div.dataset.selected = value === selectedSourceWindow ? 'true' : 'false';
    div.dataset.size = metrics.large ? 'large' : 'normal';
    div.title = `${metrics.definition}; ${copySize.label}; ${closeoutSize}`;
    div.innerHTML = `
      <span class="scope-contract-head">
        <span class="scope-contract-name">${_escHtml(metrics.label)}</span>
        <span class="scope-contract-copied" aria-hidden="true">✓ Copied</span>
        <span class="scope-contract-stats">${_escHtml(`${metrics.range} · ${metrics.turnCount} turn${metrics.turnCount === 1 ? '' : 's'}`)}</span>
      </span>
      <span class="scope-contract-sub">
        <span class="scope-contract-definition">${_escHtml(metrics.definition)}</span>
        <span class="scope-contract-use">${_escHtml(`${copySize.label} · ${closeoutSize}`)}</span>
      </span>
    `;
    decorateScopeRowCopyFlash(div, value, Date.now());
    div.addEventListener('click', () => {
      window.__aiwTraceSourceWindow = value;
      if (dropdownEls?.missionSourceWindow) dropdownEls.missionSourceWindow.value = value;
      safeRenderAgentTraceDropdown('scope_contract_click');
      updateAgentTraceSummary();
    });
    el.appendChild(div);
  }
}

function selectedSourceIdentity(row, variant, sourceWindow = DEFAULT_TRACE_SOURCE_WINDOW) {
  const lct = rowHasActiveTrace(row) ? activityDisplayTurn(row) : traceDisplayTurn(row);
  const normalizedSourceWindow = normalizeTraceSourceWindow(sourceWindow);
  const identitySourceWindow = normalizedSourceWindow;
  const backendSourceWindow = backendTraceSourceWindow(normalizedSourceWindow);
  const traceWindow = traceWindowForSource(row, normalizedSourceWindow, lct);
  const sessionId = row?.session_id || '';
  const promptSha16 = backendSourceWindow === SOURCE_WINDOW_SELECTED_TURN
    ? (lct.prompt_sha16 || '')
    : (backendSourceWindow === SOURCE_WINDOW_FULL_THREAD
      ? (traceWindow.prompt_sha16 || lct.full_thread_prompt_sha16 || '')
      : (traceWindow.prompt_sha16 || lct.trace_window_prompt_sha16 || lct.prompt_sha16 || ''));
  const turnIndexRaw = backendSourceWindow === SOURCE_WINDOW_SELECTED_TURN
    ? lct.turn_index
    : (traceWindow.end_turn_index ?? lct.turn_index);
  const turnIndex = turnIndexRaw != null ? Number(turnIndexRaw) : null;
  const turnId = backendSourceWindow === SOURCE_WINDOW_SELECTED_TURN
    ? (lct.turn_id || '')
    : (traceWindow.turn_id || lct.trace_window_turn_id || lct.turn_id || '');
  const startTurnRaw = backendSourceWindow === SOURCE_WINDOW_SELECTED_TURN
    ? turnIndexRaw
    : (traceWindow.start_turn_index ?? turnIndexRaw);
  const startTurnIndex = startTurnRaw != null ? Number(startTurnRaw) : null;
  const windowTurnCount = backendSourceWindow === SOURCE_WINDOW_SELECTED_TURN
    ? 1
    : Math.max(
      1,
      _numberOrNull(traceWindow.turn_count) || 0,
      backendSourceWindow === SOURCE_WINDOW_FULL_THREAD ? missionKnownThreadTurnCount(row, lct) : (_numberOrNull(lct.trace_window_turn_count) || 0),
    );
  const parts = [
    `session=${sessionId}`,
    `window=${identitySourceWindow}`,
    `prompt=${promptSha16 || 'noprompt'}`,
    `turn=${turnIndex != null && Number.isFinite(turnIndex) ? turnIndex : 'noturn'}`,
    `variant=${variant || ''}`,
  ];
  return {
    session_id: sessionId,
    source_window: identitySourceWindow,
    backend_source_window: backendSourceWindow,
    prompt_sha16: promptSha16,
    turn_index: turnIndex,
    turn_id: turnId,
    window_start_turn_index: startTurnIndex,
    window_turn_count: Number.isFinite(windowTurnCount) ? windowTurnCount : 1,
    variant,
    identity_key: parts.join('|'),
  };
}

function requestMissionSizeMeasurement(row, sourceWindow = selectedTraceSourceWindow()) {
  if (!row || !hasNativeBridge('measureMissionArtifact')) return false;
  const primaryVariant = tracePrimaryVariantForSource(sourceWindow);
  const primaryIdentity = selectedSourceIdentity(row, primaryVariant, sourceWindow);
  if (!primaryIdentity.identity_key || missionSizeMeasurements.has(primaryIdentity.identity_key) || missionSizeMeasurementsPending.has(primaryIdentity.identity_key)) {
    return false;
  }
  const provider = row.provider === 'claude_code' ? 'claude' : row.provider;
  if (!provider || !row.session_id) return false;
  const displayTurn = rowHasActiveTrace(row) ? activityDisplayTurn(row) : traceDisplayTurn(row);
  const activeTrace = rowHasActiveTrace(row);
  const backendSourceWindow = backendTraceSourceWindow(sourceWindow);
  const traceWindow = traceWindowForSource(row, sourceWindow, displayTurn);
  missionSizeMeasurementsPending.add(primaryIdentity.identity_key);
  const payload = {
    provider,
    session_id: row.session_id,
    mission_key: missionKey(row),
    measurement_key: primaryIdentity.identity_key,
    ui_provider: row.provider || '',
    variant: 'all',
    title: missionDisplayTitle(row, displayTurn),
    prompt_sha16: primaryIdentity.prompt_sha16 || '',
    turn_index: primaryIdentity.turn_index,
    turn_id: primaryIdentity.turn_id || '',
    force_turn_index: primaryIdentity.turn_index != null,
    use_active_turn: activeTrace,
    allow_partial: activeTrace || primaryIdentity.turn_index != null,
    source_window: backendSourceWindow,
    ui_source_window: sourceWindow,
    window_start_turn_index: backendSourceWindow === SOURCE_WINDOW_SELECTED_TURN ? (displayTurn.turn_index ?? null) : (traceWindow.start_turn_index ?? displayTurn.turn_index ?? null),
    window_turn_count: backendSourceWindow === SOURCE_WINDOW_SELECTED_TURN ? 1 : Math.max(
      1,
      _numberOrNull(traceWindow.turn_count) || 0,
      backendSourceWindow === SOURCE_WINDOW_FULL_THREAD ? missionKnownThreadTurnCount(row, displayTurn) : (_numberOrNull(displayTurn.trace_window_turn_count) || 0),
    ),
    include_prompt: true,
  };
  if (!postNative('measureMissionArtifact', payload)) {
    missionSizeMeasurementsPending.delete(primaryIdentity.identity_key);
    return false;
  }
  return true;
}

function variantArtifact(row, variant, sourceWindow = DEFAULT_TRACE_SOURCE_WINDOW) {
  const artifacts = row?.variant_artifacts || {};
  const identity = selectedSourceIdentity(row, variant, sourceWindow);
  const byIdentity = artifacts.by_source_identity || {};
  const keyed = identity.identity_key ? byIdentity[identity.identity_key] : null;
  if (keyed?.[variant]) return keyed[variant];
  if (artifacts[variant]) return artifacts[variant];
  if (variant === 'trace_capsule') return artifacts.agent_trace_capsule_text_v3 || artifacts.agent_trace_capsule_text_v2 || artifacts.agent_trace_capsule_text_v1 || artifacts.agent_trace_capsule_v1 || artifacts.trace_capsule_v1 || null;
  if (variant === 'closeout_report') return artifacts.agent_trace_closeout_report_v1 || artifacts.closeout_report_v1 || null;
  if (variant === 'packet') return artifacts.agent_trace_packet_v1 || artifacts.trace_packet || null;
  if (variant === 'denoised') return artifacts.denoised_packet_v0 || artifacts.denoised_packet || null;
  if (variant === 'compact_json') return artifacts.compact_json_v2 || null;
  return null;
}

function traceSummaryCacheState(row) {
  return String(row?.trace_summary_cache_state || '').toLowerCase();
}

function rowHasSoftStaleTraceSummary(row) {
  const state = traceSummaryCacheState(row);
  return state === 'soft_stale' || state === 'soft_stale_hit' || state.startsWith('soft_stale_');
}

function traceTurnLooksActive(turn) {
  if (!turn || !(turn.status === 'in_flight' || turn.is_complete === false)) return false;
  return true;
}

function traceDisplayTurn(row) {
  const activeTurn = rowActiveTurn(row);
  if (activeTurn) return activeTurn;
  if (row?.latest_completed_turn?.turn_index != null) return row.latest_completed_turn;
  const staleTurn = row?.stale_active_turn || {};
  if (staleTurn?.turn_index != null) return staleTurn;
  const preferred = row?.preferred_trace_turn || row?.active_turn || {};
  if (!rowHasSoftStaleTraceSummary(row) && preferred?.turn_index != null) return preferred;
  return {};
}

function traceTurnIsActive(turn, row = null) {
  if (!traceTurnLooksActive(turn)) return false;
  // A soft-stale summary is an old cached parse after the provider session file
  // changed. It may contain an active_turn from before task_complete was
  // appended, so it cannot truthfully prove RUNNING.
  if (rowHasSoftStaleTraceSummary(row)) return false;
  const activeIndex = _numberOrNull(turn.turn_index);
  const latestIndex = _numberOrNull(row?.latest_completed_turn?.turn_index);
  if (activeIndex != null && latestIndex != null && activeIndex <= latestIndex) return false;
  const activeStarted = timestampMs(turn.started_at);
  const latestCompleted = timestampMs(row?.latest_completed_turn?.completed_at);
  if (activeStarted && latestCompleted && activeStarted <= latestCompleted) return false;
  return true;
}

function rowActiveTurn(row) {
  if (traceTurnIsActive(row?.active_turn, row)) return row.active_turn;
  if (traceTurnIsActive(row?.preferred_trace_turn, row)) return row.preferred_trace_turn;
  return null;
}

function activityDisplayTurn(row) {
  return rowActiveTurn(row) || traceDisplayTurn(row);
}

function rowHasActiveTrace(row) {
  return Boolean(rowActiveTurn(row));
}

function rowHasStaleActiveTurn(row) {
  if (!rowHasSoftStaleTraceSummary(row)) return false;
  if (row?.active_turn_stale === true || row?.stale_active_turn) return true;
  return traceTurnLooksActive(row?.active_turn) || traceTurnLooksActive(row?.preferred_trace_turn);
}

function traceCopyCanUseCompletedTurnDespiteActiveSource(row, sourceWindow, activeTrace = false, stateModel = null) {
  const value = normalizeTraceSourceWindow(sourceWindow);
  if (value !== SOURCE_WINDOW_PROMPT_CYCLE || activeTrace) return false;
  const source = stateModel?.source_freshness || row?.source_freshness || {};
  const sourceState = source.source_index_state || source.state || sourceFreshnessState(row);
  if (!['source_newer_than_index', 'source_size_changed'].includes(sourceState)) return false;
  const cacheState = String(row?.trace_summary_cache_state || source.cache_state || source.reason || '').toLowerCase();
  if (!cacheState.includes('active_downgraded') && !rowHasStaleActiveTurn(row)) return false;
  const selectedTurn = traceDisplayTurn(row);
  const selectedIndex = _numberOrNull(selectedTurn?.turn_index);
  const completedIndex = _numberOrNull(row?.latest_completed_turn?.turn_index);
  if (selectedIndex == null || completedIndex == null || selectedIndex !== completedIndex) return false;
  if (traceTurnLooksActive(selectedTurn) || selectedTurn?.is_complete === false) return false;
  const knownSourceLatest = _numberOrNull(source.current_latest_turn_index);
  if (knownSourceLatest != null && knownSourceLatest > selectedIndex) return false;
  return true;
}

function sourceFreshnessState(row) {
  return (row?.source_freshness || {}).state || '';
}

function isLiveSourceUpdating(row) {
  return rowHasActiveTrace(row) && ['source_newer_than_index', 'source_size_changed'].includes(sourceFreshnessState(row));
}

function isSourceIndexStale(row) {
  if (isLiveSourceUpdating(row)) return false;
  return ['source_newer_than_index', 'source_size_changed', 'source_missing'].includes(sourceFreshnessState(row));
}

function canonicalDiffState(value) {
  const raw = String(value || '').trim().toLowerCase();
  if (!raw) return '';
  if (['exact_hunks_attached', 'exact_plus_minus_attached', 'available', 'attached', 'inline_git_diff_patch', 'final_delta_attached'].includes(raw)) return 'exact_hunks_attached';
  if (['compact_mode_diff_summary_only', 'compact_summary_only', 'summary_only', 'full_thread_concise'].includes(raw)) return 'compact_summary_only';
  if (['ui_summary_only', 'visible_ui_diff_only', 'ui_diff_only'].includes(raw)) return 'ui_summary_only';
  if (['commit_without_diff', 'commit_diff_missing'].includes(raw)) return 'commit_diff_missing';
  if (raw === 'missing' || raw.includes('missing_exact') || raw.includes('missing_plus')) return 'missing_exact_plus_minus';
  if (raw.includes('no_diff_evidence')) return 'no_diff_evidence';
  return raw.replace(/[^a-z0-9_]+/g, '_');
}

function boolish(value) {
  if (value === true || value === false) return value;
  const raw = String(value || '').trim().toLowerCase();
  if (raw === 'true') return true;
  if (raw === 'false') return false;
  return Boolean(value);
}

function artifactTraceCounts(artifact) {
  const summary = objectOrEmpty(artifact?.content_summary);
  const counts = objectOrEmpty(artifact?.trace_counts);
  const diffStateObj = objectOrEmpty(artifact?.diff_state || counts.diff_state || summary.diff_state);
  const out = { ...summary, ...counts };
  const editCount = _numberOrNull(out.edit_path_count ?? out.edit_count ?? summary.edit_count);
  if (editCount != null) out.edit_path_count = editCount;
  const commandCount = _numberOrNull(out.command_count);
  if (commandCount != null) out.command_count = commandCount;
  const validationCount = _numberOrNull(out.validation_count ?? out.check_count);
  if (validationCount != null) out.validation_count = validationCount;
  const uiDiffCount = _numberOrNull(out.ui_diff_count ?? out.visible_ui_diff_count);
  if (uiDiffCount != null) out.ui_diff_count = uiDiffCount;
  if (out.closeout_present != null) out.closeout_present = boolish(out.closeout_present);
  if (out.full_thread_available != null) out.full_thread_available = boolish(out.full_thread_available);
  if (out.selected_window_only != null) out.selected_window_only = boolish(out.selected_window_only);
  if (out.no_edit_claim_allowed != null) out.no_edit_claim_allowed = boolish(out.no_edit_claim_allowed);
  if (out.substrate_diff_required != null) out.substrate_diff_required = boolish(out.substrate_diff_required);
  if (out.commit_diff_missing != null) out.commit_diff_missing = boolish(out.commit_diff_missing);
  if (out.final_delta_attached != null) out.final_delta_attached = boolish(out.final_delta_attached);
  if (out.edit_event_log_attached != null) out.edit_event_log_attached = boolish(out.edit_event_log_attached);
  out.substrate_diff = canonicalDiffState(out.substrate_diff || out.diff_state || diffStateObj.state || summary.substrate_diff);
  out.diff_state = out.substrate_diff || canonicalDiffState(diffStateObj.state);
  return out;
}

function sourceFreshnessContract(row, artifact, variant, sourceWindow = DEFAULT_TRACE_SOURCE_WINDOW) {
  const identity = selectedSourceIdentity(row, variant, sourceWindow);
  const sourceFreshness = objectOrEmpty(row?.source_freshness);
  const sourceState = sourceFreshnessState(row) || 'unknown';
  const artifactTurn = artifact?.turn_index != null ? Number(artifact.turn_index) : null;
  const artifactWindow = artifact?.source_window || '';
  const artifactUiWindow = artifact?.ui_source_window
    || artifact?.requested_source_window
    || artifact?.window_anchor?.ui_source_window
    || '';
  const artifactPrompt = artifact?.prompt_sha16 || '';
  const artifactSourceSha16 = artifact?.source_sha16 || artifact?.window_anchor?.source_sha16 || artifact?.trace_counts?.source_sha16 || '';
  const currentTurnCount = _numberOrNull(sourceFreshness.current_turn_count);
  const indexTurnCount = _numberOrNull(sourceFreshness.index_turn_count);
  const completedTurnSafeDespiteActiveSource = traceCopyCanUseCompletedTurnDespiteActiveSource(
    row,
    sourceWindow,
    false,
    { source_freshness: sourceFreshness },
  );
  const reasons = [];
  if (!artifact?.path) reasons.push('missing_artifact');
  const expectedSchema = EXPECTED_VARIANT_SCHEMAS[variant] || '';
  if (artifact?.path && expectedSchema && artifact.schema_version !== expectedSchema) reasons.push('schema_mismatch');
  const expectedRole = EXPECTED_VARIANT_ROLES[variant] || '';
  if (artifact?.path && expectedRole && artifact.artifact_role !== expectedRole) reasons.push('artifact_role_mismatch');
  const budget = VARIANT_SIZE_BUDGETS[variant] || 0;
  const artifactBytes = Number(artifact?.bytes || 0);
  const sizeStatus = artifact?.size_contract?.status || '';
  if (artifact?.path && ((budget && artifactBytes > budget) || (!['trace_capsule', 'closeout_report'].includes(variant) && sizeStatus === 'over_budget'))) {
    reasons.push('size_over_budget');
  }
  if (artifact?.path && ['trace_capsule', 'closeout_report', 'packet', 'denoised', 'compact_json'].includes(variant)) {
    const counts = artifactTraceCounts(artifact);
    const commandCount = Number(counts.command_count ?? 0);
    const hasCloseout = counts.closeout_present === true;
    if ((!Number.isFinite(commandCount) || commandCount <= 0) && !(variant === 'closeout_report' && hasCloseout)) {
      reasons.push('empty_trace');
    }
  }
  if (artifact?.path && !artifactWindow && !artifactUiWindow) {
    reasons.push('missing_source_window');
  } else if (artifact?.path) {
    const uiMatches = artifactUiWindow && normalizeTraceSourceWindow(artifactUiWindow) === identity.source_window;
    const backendMatches = artifactWindow && normalizeTraceSourceWindow(artifactWindow) === identity.backend_source_window;
    if (!uiMatches && !backendMatches) reasons.push('source_window_mismatch');
  }

  // Source staleness never waives selected artifact identity. It only changes
  // the copy action from normal copy to refresh/block so old turn stats cannot
  // bleed into the currently selected row.
  if (artifact?.path && identity.prompt_sha16 && (!artifactPrompt || artifactPrompt !== identity.prompt_sha16)) reasons.push('prompt_mismatch');
  if (artifact?.path && identity.turn_index != null && (!Number.isFinite(artifactTurn) || artifactTurn !== identity.turn_index)) reasons.push('turn_mismatch');
  if (isLiveSourceUpdating(row)) reasons.push('live_source_updated');
  if (['source_newer_than_index', 'source_size_changed'].includes(sourceState) && !completedTurnSafeDespiteActiveSource) reasons.push('source_index_stale');
  if (sourceState === 'source_missing') reasons.push('source_missing');
  if (currentTurnCount != null && identity.window_turn_count != null && currentTurnCount > Number(identity.window_turn_count || 0) && sourceState !== 'current' && !completedTurnSafeDespiteActiveSource) {
    reasons.push('source_turn_count_ahead_of_selected_index');
  }

  const hardBlockReasons = reasons.filter((reason) => ['source_missing', 'empty_trace', 'size_over_budget', 'schema_mismatch', 'artifact_role_mismatch'].includes(reason));
  const action = hardBlockReasons.length
    ? 'block_copy'
    : reasons.length
      ? 'refresh_before_copy'
      : 'allow_copy';
  return {
    schema_version: 'agent_trace_source_freshness_v1',
    source_index_state: sourceState,
    selected_turn_id: identity.turn_id || '',
    selected_turn_index: identity.turn_index,
    index_turn_id: traceDisplayTurn(row)?.turn_id || '',
    index_turn_index: traceDisplayTurn(row)?.turn_index ?? null,
    capsule_turn_id: artifact?.turn_id || artifact?.window_anchor?.turn_id || '',
    capsule_turn_index: artifactTurn,
    source_sha16: sourceFreshness.current_sha16 || row?.source_sha16 || '',
    index_source_sha16: sourceFreshness.index_sha16 || row?.index_source_sha16 || '',
    capsule_source_sha16: artifactSourceSha16,
    current_turn_count: currentTurnCount,
    index_turn_count: indexTurnCount,
    current_latest_turn_index: _numberOrNull(sourceFreshness.current_latest_turn_index),
    capsule_source_window: artifactWindow || '',
    capsule_ui_source_window: artifactUiWindow || '',
    expected_source_window: identity.source_window,
    expected_backend_source_window: identity.backend_source_window,
    expected_prompt_sha16: identity.prompt_sha16 || '',
    capsule_prompt_sha16: artifactPrompt || '',
    mismatch_reason: reasons.join(',') || 'source_identity_current',
    action,
    ready: action === 'allow_copy',
    state: action === 'allow_copy' ? 'current' : (action === 'block_copy' ? 'blocked_artifact' : 'stale_artifact'),
    identity,
  };
}

function traceIdentityPolicy(row, activeTrace = false) {
  const sourceState = sourceFreshnessState(row) || '';
  const cacheState = String(row?.trace_summary_cache_state || '').toLowerCase();
  const artifactState = String(row?.artifact_freshness?.state || '').toLowerCase();
  const staleSummary = cacheState.includes('stale');
  const liveOrStaleSource = isLiveSourceUpdating(row) || isSourceIndexStale(row);
  const allowPromptRebind = Boolean(activeTrace && !isSourceIndexStale(row));
  const reasons = [];
  if (activeTrace) reasons.push('partial_or_current_turn');
  if (isLiveSourceUpdating(row)) reasons.push('live_source_updating');
  if (isSourceIndexStale(row)) reasons.push(sourceState || 'source_index_stale');
  if (staleSummary) reasons.push(cacheState);
  return {
    allow_prompt_rebind_if_source_stale: allowPromptRebind,
    allow_prompt_rebind_for_active_trace: allowPromptRebind,
    source_index_state: sourceState,
    trace_summary_cache_state: cacheState,
    artifact_freshness_state: artifactState,
    identity_rebind_reason: reasons.join(',') || 'source_identity_current',
  };
}

function traceCopyNeedsSourceLatest(row, sourceWindow, activeTrace, stateModel = null) {
  const value = normalizeTraceSourceWindow(sourceWindow);
  if (value === SOURCE_WINDOW_SELECTED_TURN) return false;
  const sourceAction = stateModel?.source_freshness?.action || '';
  return Boolean(
    activeTrace
      || traceCopyCanUseSourceLatestFallback(row, value, activeTrace, stateModel)
      || sourceAction === 'refresh_before_copy'
  );
}

function traceCopyCanUseSourceLatestFallback(row, sourceWindow, activeTrace, stateModel = null) {
  const value = normalizeTraceSourceWindow(sourceWindow);
  if (value === SOURCE_WINDOW_SELECTED_TURN || activeTrace) return false;
  const fullThreadScope = backendTraceSourceWindow(value) === SOURCE_WINDOW_FULL_THREAD;
  const source = stateModel?.source_freshness || {};
  const sourceState = source.source_index_state || sourceFreshnessState(row);
  if (sourceState === 'source_missing' || source.action === 'block_copy') return false;
  const cacheState = String(row?.trace_summary_cache_state || source.cache_state || '').toLowerCase();
  const mismatch = String(source.mismatch_reason || source.reason || '');
  const staleSummary = rowHasSoftStaleTraceSummary(row) || cacheState.includes('stale');
  const currentLatest = _numberOrNull(source.current_latest_turn_index);
  const selectedTurn = _numberOrNull(source.selected_turn_index) ?? _numberOrNull(traceDisplayTurn(row)?.turn_index);
  const newerSourceLatestExists = currentLatest != null && selectedTurn != null && currentLatest > selectedTurn;
  if (!fullThreadScope && cacheState.includes('active_downgraded') && !newerSourceLatestExists) return false;
  return Boolean(
    ['source_newer_than_index', 'source_size_changed'].includes(sourceState)
      || mismatch.includes('source_index_stale')
      || mismatch.includes('source_turn_count_ahead_of_selected_index')
      || staleSummary
      || newerSourceLatestExists
      || (currentLatest != null && selectedTurn != null && currentLatest >= selectedTurn && source.action === 'refresh_before_copy')
  );
}

function traceCopyRequiresVisibleIndexRefresh(row, sourceWindow, activeTrace, stateModel = null) {
  const value = normalizeTraceSourceWindow(sourceWindow);
  if (value === SOURCE_WINDOW_SELECTED_TURN || activeTrace) return false;
  if (traceCopyCanUseCompletedTurnDespiteActiveSource(row, value, activeTrace, stateModel)) return false;
  if (traceCopyCanUseSourceLatestFallback(row, value, activeTrace, stateModel)) return false;
  const source = stateModel?.source_freshness || {};
  const sourceState = source.source_index_state || sourceFreshnessState(row);
  if (['source_newer_than_index', 'source_size_changed', 'source_missing'].includes(sourceState)) return true;
  if (rowHasSoftStaleTraceSummary(row)) return true;
  const mismatch = String(source.mismatch_reason || source.reason || '');
  return source.action === 'refresh_before_copy'
    && (mismatch.includes('source_index_stale') || mismatch.includes('source_turn_count_ahead_of_selected_index'));
}

function variantArtifactCurrentness(row, artifact, variant, sourceWindow = DEFAULT_TRACE_SOURCE_WINDOW) {
  if (!artifact?.path) {
    const identity = selectedSourceIdentity(row, variant, sourceWindow);
    return { state: 'missing', ready: false, reason: 'missing_artifact', identity, source_freshness: sourceFreshnessContract(row, artifact, variant, sourceWindow) };
  }
  const contract = sourceFreshnessContract(row, artifact, variant, sourceWindow);
  return {
    state: contract.state,
    ready: contract.ready,
    reason: contract.mismatch_reason === 'source_identity_current' ? '' : contract.mismatch_reason,
    identity: contract.identity,
    source_freshness: contract,
  };
}

function sourceIndexStateLabel(row) {
  if (isLiveSourceUpdating(row)) return 'LIVE SOURCE';
  const sourceState = sourceFreshnessState(row);
  if (sourceState === 'source_newer_than_index') return 'SOURCE INDEX STALE';
  if (sourceState === 'source_size_changed') return 'SOURCE SIZE CHANGED';
  if (sourceState === 'source_missing') return 'SOURCE MISSING';
  return '';
}

/**
 * Mission status receipts must land in the visible 72px capsule, not on
 * els.status (#status lives in .panel below the bar and is invisible to the
 * operator unless they've opened the full structurer panel). Write to
 * selectedMissionEl so the receipt shows up where the click happened. Auto-
 * restore after timeoutMs so the selected mission summary returns.
 */
let _missionStatusRestoreTimer = 0;
function setMissionBarStatus(text, { timeoutMs = 6000 } = {}) {
  if (els.status) els.status.textContent = text;
  if (!selectedMissionEl) return;
  selectedMissionEl.textContent = text;
  if (_missionStatusRestoreTimer) {
    window.clearTimeout(_missionStatusRestoreTimer);
    _missionStatusRestoreTimer = 0;
  }
  _missionStatusRestoreTimer = window.setTimeout(() => {
    _missionStatusRestoreTimer = 0;
    renderSelectedMission();
  }, timeoutMs);
}

function activeMissionRows() {
  if (!missionIndex) return [];
  return Array.isArray(missionIndex.active_rows) ? missionIndex.active_rows : [];
}

function inactiveMissionRows() {
  if (!missionIndex) return [];
  return Array.isArray(missionIndex.inactive_rows) ? missionIndex.inactive_rows : [];
}

function allMissionRows() {
  const out = [];
  const seen = new Set();
  for (const row of activeMissionRows().concat(inactiveMissionRows())) {
    const key = missionKey(row);
    if (key && seen.has(key)) continue;
    if (key) seen.add(key);
    out.push(row);
  }
  return out;
}

function _missionSortTime(row) {
  const turn = activityDisplayTurn(row);
  return timestampMs(row?.last_activity_at || turn.completed_at || turn.started_at || row?.updated_at || row?.generated_at || '') || 0;
}

function _missionLastActivityMs(row) {
  const direct = timestampMs(row?.last_activity_at);
  if (direct != null) return direct;
  return _missionSortTime(row) || 0;
}

function missionAutoRefreshSignature(row, reason) {
  const turn = activityDisplayTurn(row);
  return [
    reason || 'watch',
    _missionLastActivityMs(row) || 0,
    turn?.turn_index ?? '',
    turn?.turn_id || '',
    row?.active_turn_stale === true ? 'active_stale' : '',
    row?.source_freshness?.state || '',
    row?.source_freshness?.current_mtime_utc || row?.source_freshness?.mtime_ms || '',
    row?.source_freshness?.current_size_bytes || row?.source_freshness?.size || '',
  ].join('|');
}

function unseenMissionAutoRefreshRows(rows, reason) {
  const liveKeys = new Set(activeMissionRows().map((row) => missionKey(row)).filter(Boolean));
  for (const key of Array.from(missionAutoRefreshSignatureByKey.keys())) {
    if (!liveKeys.has(key)) missionAutoRefreshSignatureByKey.delete(key);
  }
  return rows.filter((row) => {
    const key = missionKey(row);
    if (!key) return false;
    const signature = missionAutoRefreshSignature(row, reason);
    if (!signature || missionAutoRefreshSignatureByKey.get(key) === signature) return false;
    missionAutoRefreshSignatureByKey.set(key, signature);
    return true;
  });
}

function _missionLastCompletedAtMs(row) {
  return timestampMs(row?.latest_completed_turn?.completed_at);
}

// Visible mission rows = active rows plus the inactive rows that are still
// operator-relevant: selected, just finished, recently copied, search-matched,
// or explicitly revealed. Old inactive rows remain reachable through the footer
// toggle without polluting the default cockpit queue.
function visibleMissionRows() {
  if (!missionIndex) return [];
  const active = activeMissionRows();
  const inactive = inactiveMissionRows();
  if (!inactive.length) return active;
  const now = Date.now();
  const seen = new Set(active.map((r) => missionKey(r)));
  const includeAllInactive = showInactiveMissions || Boolean(dropdownSearch);
  const visibleInactive = [];
  for (const row of inactive) {
    const k = missionKey(row);
    if (seen.has(k)) continue;
    if (includeAllInactive || k === selectedMissionKey) {
      visibleInactive.push(row);
      seen.add(k);
      continue;
    }
    const copyEntry = k ? missionViewState.copyByKey.get(k) : null;
    const copyAnchor = Math.max(copyEntry?.successAt || 0, copyEntry?.startedAt || 0, copyEntry?.failureAt || 0);
    if (copyAnchor && now - copyAnchor < MISSION_PENDING_COPY_TTL_MS) {
      visibleInactive.push(row);
      seen.add(k);
      continue;
    }
    const completed = _missionLastCompletedAtMs(row) || _missionLastActivityMs(row);
    if (!completed) continue;
    if (now - completed > MISSION_JUST_FINISHED_MS) continue;
    visibleInactive.push(row);
    seen.add(k);
  }
  if (!visibleInactive.length) return active;
  return active.concat(visibleInactive);
}

function hiddenInactiveCount() {
  if (showInactiveMissions || dropdownSearch || !missionIndex) return 0;
  const inactive = inactiveMissionRows();
  if (!inactive.length) return 0;
  const visible = new Set(visibleMissionRows().map((row) => missionKey(row)).filter(Boolean));
  return inactive.filter((row) => {
    const key = missionKey(row);
    return key && !visible.has(key);
  }).length;
}

function rememberMissionCopyStart(key, meta = {}) {
  if (!key) return;
  const entry = missionViewState.copyByKey.get(key) || {};
  entry.startedAt = Date.now();
  entry.successAt = null;
  entry.failureAt = null;
  entry.error = null;
  Object.assign(entry, meta || {});
  missionViewState.copyByKey.set(key, entry);
  scheduleMissionLifecycleTick();
}

function rememberMissionCopySuccess(key, meta = {}) {
  if (!key) return;
  const entry = missionViewState.copyByKey.get(key) || {};
  if (!entry.startedAt) entry.startedAt = Date.now();
  entry.successAt = Date.now();
  entry.failureAt = null;
  Object.assign(entry, meta || {});
  missionViewState.copyByKey.set(key, entry);
  scheduleMissionLifecycleTick();
}

function rememberMissionCopyFailure(key, error = '') {
  if (!key) return;
  const entry = missionViewState.copyByKey.get(key) || {};
  if (!entry.startedAt) entry.startedAt = Date.now();
  entry.failureAt = Date.now();
  entry.error = error || '';
  missionViewState.copyByKey.set(key, entry);
  scheduleMissionLifecycleTick();
}

function pruneMissionViewState(now) {
  const copyTtl = MISSION_PENDING_COPY_TTL_MS + MISSION_COPY_ACK_MS;
  for (const [k, v] of missionViewState.copyByKey) {
    const anchor = Math.max(v?.successAt || 0, v?.failureAt || 0, v?.startedAt || 0);
    if (!anchor || now - anchor > copyTtl) missionViewState.copyByKey.delete(k);
  }
  // seen / active maps are bounded by the index size, but trim entries we have
  // not seen in over a day so the maps cannot grow unboundedly across sessions.
  const seenTtl = 24 * 60 * 60_000;
  for (const [k, ms] of missionViewState.seenAtByKey) {
    if (now - ms > seenTtl) {
      missionViewState.seenAtByKey.delete(k);
      missionViewState.activeSeenByKey.delete(k);
      missionViewState.completedTurnByKey.delete(k);
      missionViewState.finishedAtByKey.delete(k);
    }
  }
  for (const [k, ms] of missionViewState.finishedAtByKey) {
    if (now - ms > MISSION_JUST_FINISHED_MS + 5 * 60_000) missionViewState.finishedAtByKey.delete(k);
  }
}

function completedTurnIndexForRow(row) {
  return _numberOrNull(row?.latest_completed_turn?.turn_index);
}

function noteMissionCompletionTransition(row, reason, now) {
  const key = missionKey(row);
  if (!key) return;
  missionViewState.finishedAtByKey.set(key, now);
  if (isAgentTraceWorkbenchActive()) {
    const title = missionDisplayTitle(row, traceDisplayTurn(row)) || shortSessionId(row?.session_id);
    setMissionReceipt(`✓ ${providerLabel(row?.provider)} finished ${title}; refreshing quietly for final state.`);
  }
  scheduleMissionRefresh(reason || 'completed_turn_transition', { quiet: true, delayMs: MISSION_REFRESH_DEBOUNCE_MS });
}

// observeMissionIndexUpdate — first-render rule is load-bearing:
//   * On the very first observed index, record seenAt for every key WITHOUT
//     marking the row as newly_seen. The visible flag is gated on
//     missionViewState.initializedSeenKeys.
//   * On subsequent observations, any key not previously seen gets seenAt=now
//     and will paint as newly_seen for MISSION_NEW_ROW_MS.
// activeSeenByKey tracks the previous active/inactive observation per key so
// the classifier can detect the live→inactive transition for 'just_finished'.
function observeMissionIndexUpdate(rows) {
  if (!Array.isArray(rows)) return;
  const now = Date.now();
  const present = new Set();
  const initialized = missionViewState.initializedSeenKeys;
  for (const row of rows) {
    const key = missionKey(row);
    if (!key) continue;
    present.add(key);
    const activeNow = rowIsLiveMission(row);
    const completedTurn = completedTurnIndexForRow(row);
    const wasActive = missionViewState.activeSeenByKey.get(key) === true;
    const previousCompletedTurn = missionViewState.completedTurnByKey.get(key);
    const completedAdvanced = completedTurn != null
      && previousCompletedTurn != null
      && completedTurn > previousCompletedTurn;
    if (!rowIsOldPrefixRetired(row) && initialized && ((wasActive && !activeNow) || (wasActive && completedAdvanced))) {
      noteMissionCompletionTransition(row, wasActive && !activeNow ? 'active_turn_finished' : 'completed_turn_advanced', now);
    }
    if (!missionViewState.seenAtByKey.has(key)) {
      // On first paint, backdate seenAt past the new-row window so the row is
      // NOT classified as newly_seen until a later refresh actually introduces it.
      missionViewState.seenAtByKey.set(key, initialized ? now : now - MISSION_NEW_ROW_MS - 1000);
    }
    missionViewState.activeSeenByKey.set(key, activeNow);
    if (completedTurn != null) missionViewState.completedTurnByKey.set(key, completedTurn);
  }
  missionViewState.initializedSeenKeys = true;
  // Forget rows that disappeared from the index entirely so just_finished
  // memory does not falsely fire if they reappear later.
  for (const k of Array.from(missionViewState.activeSeenByKey.keys())) {
    if (!present.has(k)) {
      missionViewState.activeSeenByKey.delete(k);
      missionViewState.completedTurnByKey.delete(k);
    }
  }
}

function missionViewStateForRow(row, now = Date.now()) {
  const key = missionKey(row);
  const activeTrace = rowHasActiveTrace(row);
  const activeGoal = rowHasActiveGoal(row);
  const activeNow = activeTrace || activeGoal;
  const staleActive = !activeGoal && rowHasStaleActiveTurn(row);
  const wasActive = missionViewState.activeSeenByKey.get(key) === true;
  const lastActMs = _missionLastActivityMs(row);
  const completedAtMs = _missionLastCompletedAtMs(row);
  const finishedAt = missionViewState.finishedAtByKey.get(key);
  const transitionedToFinished = (wasActive && !activeNow) || (finishedAt != null && (now - finishedAt) < MISSION_JUST_FINISHED_MS);
  const displayTurn = activeTrace ? activityDisplayTurn(row) : traceDisplayTurn(row);
  const c = missionViewState.copyByKey.get(key);
  const lifecycle = deriveMissionLifecycle({
    row,
    key,
    now,
    activeNow: activeTrace,
    activeGoal,
    staleActive,
    wasActive,
    lastActivityMs: lastActMs,
    completedAtMs,
    activeStartedAtMs: timestampMs(row?.active_turn?.started_at || displayTurn?.started_at),
    transitionedToFinished,
    displayTurn,
    hasTurn: displayTurn?.turn_index != null,
    copyEntry: c,
    copyAckMs: MISSION_COPY_ACK_MS,
    pendingCopyTtlMs: MISSION_PENDING_COPY_TTL_MS,
    justFinishedMs: MISSION_JUST_FINISHED_MS,
    recentActivityMs: MISSION_RECENT_ACTIVITY_MS,
    liveActivityMs: MISSION_LIVE_ACTIVITY_MS,
    idleThresholdMs: MISSION_IDLE_THRESHOLD_MS,
  });

  // Novelty layer.
  const seenAt = missionViewState.seenAtByKey.get(key);
  const isNewlySeen = missionViewState.initializedSeenKeys
    && seenAt != null
    && (now - seenAt) < MISSION_NEW_ROW_MS;
  const novelty = isNewlySeen ? 'newly_seen' : 'known';

  return {
    activity: lifecycle.activity,
    novelty,
    copy: lifecycle.copy,
    key,
    copyEntry: c || null,
    retired: lifecycle.retired,
    lifecycle,
  };
}

function missionViewStateGlyph(view) {
  // One glyph per row — picked by priority so the row never overcrowds.
  if (view.lifecycle?.glyph) {
    const baseTitle = view.lifecycle.glyph.title || '';
    const title = view.lifecycle.revival?.by === 'refresh_copy_capture'
        && view.copy === 'just_copied'
        && !baseTitle.toLowerCase().includes('revived by copy')
      ? `revived by copy · ${view.lifecycle.glyph.title}`
      : view.lifecycle.glyph.title;
    return { glyph: view.lifecycle.glyph.glyph, title };
  }
  if (view.activity === 'retired') return { glyph: '×', title: 'retired by old-prefix title' };
  if (view.copy === 'copy_failed') {
    const reason = String(view.copyEntry?.error || '').trim();
    return { glyph: '✗', title: reason ? `copy failed — ${reason}` : 'copy failed — see receipt' };
  }
  if (view.copy === 'pending_after_copy') return { glyph: '⧖', title: 'waiting for follow-up response; clears after 25m idle' };
  if (view.copy === 'just_copied') {
    const summary = missionCopySummary(view.copyEntry, Date.now(), { includeBytes: false });
    return { glyph: '✓', title: `copied${summary ? ` · ${summary}` : ''}` };
  }
  if (view.copy === 'copying') return { glyph: '⋯', title: 'copying…' };
  if (view.activity === 'live') return { glyph: '●', title: 'running — active response in flight' };
  if (view.activity === 'just_finished') return { glyph: '✓', title: 'finished — ready to copy' };
  if (view.activity === 'checking') return { glyph: '⋯', title: 'checking stale/open turn state' };
  if (view.activity === 'recent') return { glyph: '◆', title: 'recent activity' };
  if (view.activity === 'idle') return { glyph: '·', title: 'idle >25m' };
  return { glyph: '', title: '' };
}

function missionWorkflowPill(row, view, artifactLabel = null) {
  const artifact = artifactLabel?.text ? `Artifact ${String(artifactLabel.text).toLowerCase()}. ` : '';
  const cache = rowHasSoftStaleTraceSummary(row) && !rowHasActiveGoal(row)
    ? 'Stale active cache cannot prove running; checking source. '
    : '';
  if (view.lifecycle?.pill) {
    const baseTitle = view.lifecycle.pill.title || '';
    const revival = view.lifecycle.revival?.by === 'refresh_copy_capture'
        && view.copy === 'just_copied'
        && !baseTitle.toLowerCase().includes('revived by copy')
      ? 'Revived by copy. '
      : '';
    return {
      text: view.lifecycle.pill.text,
      cls: view.lifecycle.pill.cls,
      title: `${artifact}${cache}${revival}${view.lifecycle.pill.title}.`,
    };
  }
  const turn = activityDisplayTurn(row);
  const hasTurn = turn.turn_index != null;
  if (view.activity === 'retired' || rowIsOldPrefixRetired(row)) {
    return { text: 'RETIRED', cls: 'retired', title: `${artifact}${cache}Title starts with "old"; retired from active mission flow.` };
  }
  if (view.copy === 'copy_failed') {
    return { text: 'COPY FAILED', cls: 'copy_failed', title: `${artifact}${cache}Copy failed; see receipt.` };
  }
  if (view.copy === 'copying') {
    return { text: 'COPYING', cls: 'copying', title: `${artifact}${cache}Writing the selected bundle to clipboard.` };
  }
  if (view.copy === 'just_copied') {
    const summary = missionCopySummary(view.copyEntry, Date.now());
    return { text: 'COPIED', cls: 'copied', title: `${artifact}${cache}Copied${summary ? ` · ${summary}` : ''}.` };
  }
  if (view.copy === 'pending_after_copy') {
    const summary = missionCopySummary(view.copyEntry, Date.now(), { includeBytes: false });
    return { text: 'TYPE B WAIT', cls: 'waiting', title: `${artifact}${cache}waiting_kind=type_b_response_expected. Copied${summary ? ` · ${summary}` : ''}; waiting for a follow-up response. Clears after 25 minutes with no new source activity.` };
  }
  if (view.activity === 'live') {
    return { text: 'RUNNING', cls: 'running', title: `${artifact}${cache}Active response in flight.` };
  }
  if (view.activity === 'checking') {
    return { text: 'CHECKING', cls: 'checking', title: `${artifact}${cache}Checking the changed source before deciding running or finished.` };
  }
  if (!hasTurn) {
    return { text: 'NO TURN', cls: 'partial', title: `${artifact}${cache}No trace turn is available yet.` };
  }
  if (view.activity === 'idle') {
    return { text: 'INACTIVE', cls: 'inactive', title: `${artifact}${cache}No source activity for 25 minutes.` };
  }
  return { text: 'FINISHED', cls: 'finished', title: `${artifact}${cache}Response finished; copy it to start the waiting-for-response window.` };
}

function markMissionRowsUserScrolling(scrollTop = null, now = Date.now()) {
  missionRowsUserScrollUntil = Math.max(missionRowsUserScrollUntil, now + MISSION_SCROLL_SETTLE_MS);
  const top = Number(scrollTop);
  if (!Number.isFinite(top)) return;
  const previousTop = Number.isFinite(missionRowsLastScrollTop) ? missionRowsLastScrollTop : top;
  const deltaPx = Math.abs(top - previousTop);
  const elapsedMs = missionRowsLastScrollAt ? Math.max(1, now - missionRowsLastScrollAt) : 0;
  const pxPerMs = elapsedMs ? deltaPx / elapsedMs : 0;
  if (deltaPx >= MISSION_FAST_SCROLL_DELTA_PX || pxPerMs >= MISSION_FAST_SCROLL_MIN_PX_PER_MS) {
    missionRowsFastScrollUntil = Math.max(missionRowsFastScrollUntil, now + MISSION_FAST_SCROLL_HOLD_MS);
  }
  missionRowsLastScrollTop = top;
  missionRowsLastScrollAt = now;
}

function missionRowsScrollSettling(now = Date.now()) {
  return now < missionRowsUserScrollUntil;
}

function missionRowsFastScrolling(now = Date.now()) {
  return now < missionRowsFastScrollUntil;
}

function missionRowsScrollProfile(now = Date.now()) {
  const fast = missionRowsFastScrolling(now);
  return fast
    ? {
        profile: 'fast',
        overscanRows: MISSION_FAST_RENDER_OVERSCAN_ROWS,
        windowStepRows: MISSION_FAST_RENDER_WINDOW_STEP_ROWS,
        fastScrolling: true,
      }
    : {
        profile: 'normal',
        overscanRows: MISSION_RENDER_OVERSCAN_ROWS,
        windowStepRows: MISSION_RENDER_WINDOW_STEP_ROWS,
        fastScrolling: false,
      };
}

function delayUntilMissionRowsScrollSettled(now = Date.now()) {
  return Math.max(0, missionRowsUserScrollUntil - now);
}

function settleMissionRowsInteractionNow() {
  missionRowsUserScrollUntil = 0;
  missionRowsFastScrollUntil = 0;
  if (missionRowsScrollRaf) {
    window.cancelAnimationFrame?.(missionRowsScrollRaf);
    missionRowsScrollRaf = 0;
  }
  if (missionRowsDeferredRenderTimer) {
    window.clearTimeout(missionRowsDeferredRenderTimer);
    missionRowsDeferredRenderTimer = 0;
    missionRowsDeferredRenderReason = '';
  }
  updateMissionRowsScrollAffordance();
}

function shouldDeferMissionRenderForScroll(reason = 'render') {
  const key = String(reason || 'render');
  return MISSION_SCROLL_DEFER_RENDER_REASONS.has(key)
    && isAgentTraceWorkbenchActive()
    && missionRowsScrollSettling();
}

function scheduleMissionRenderAfterScroll(reason = 'render') {
  const now = Date.now();
  const key = String(reason || 'render');
  missionRowsDeferredRenderReason = coalesceMissionRenderReason(missionRowsDeferredRenderReason, key);
  const delay = Math.max(60, delayUntilMissionRowsScrollSettled(now) + 32);
  if (missionRowsDeferredRenderTimer) window.clearTimeout(missionRowsDeferredRenderTimer);
  lastMissionRowsDeferredRenderStats = {
    reason: missionRowsDeferredRenderReason,
    delay_ms: delay,
    queued_at: now,
    flushed_at: 0,
    count: (lastMissionRowsDeferredRenderStats.count || 0) + 1,
  };
  missionRowsDeferredRenderTimer = window.setTimeout(() => {
    const queuedReason = missionRowsDeferredRenderReason || key;
    missionRowsDeferredRenderTimer = 0;
    missionRowsDeferredRenderReason = '';
    lastMissionRowsDeferredRenderStats = {
      ...lastMissionRowsDeferredRenderStats,
      reason: queuedReason,
      flushed_at: Date.now(),
    };
    if (!isAgentTraceWorkbenchActive()) return;
    scheduleMissionDropdownRender(queuedReason);
  }, delay);
  return true;
}

function scheduleMissionLifecycleTick(delayMs = MISSION_LIFECYCLE_TICK_MS) {
  if (missionLifecycleTickTimer) return;
  if (activeDropdown !== 'agent_trace') return;
  const parsedDelayMs = Number(delayMs);
  const delay = Number.isFinite(parsedDelayMs)
    ? Math.max(0, parsedDelayMs)
    : MISSION_LIFECYCLE_TICK_MS;
  missionLifecycleTickTimer = window.setTimeout(() => {
    missionLifecycleTickTimer = 0;
    if (activeDropdown !== 'agent_trace') return;
    if (missionRowsScrollSettling()) {
      scheduleMissionLifecycleTick(Math.max(60, delayUntilMissionRowsScrollSettled() + 32));
      return;
    }
    safeRenderAgentTraceDropdown('lifecycle_tick');
    try { renderMissionRail(); } catch (_) {}
  }, delay);
}

function clearMissionFinishedAutoRefresh() {
  if (missionFinishedRefreshTimer) {
    window.clearTimeout(missionFinishedRefreshTimer);
    missionFinishedRefreshTimer = 0;
  }
}

function shouldWatchMissionFinishedRefresh() {
  return document.visibilityState !== 'hidden'
    && (isAgentTraceWorkbenchActive() || isWindowShellMode() || Boolean(missionRailEl));
}

function scheduleMissionRefresh(reason = 'watch', { quiet = true, delayMs = MISSION_REFRESH_DEBOUNCE_MS } = {}) {
  if (!shouldWatchMissionFinishedRefresh()) return false;
  if (missionIndexRefreshPending) {
    if (!quiet) {
      missionIndexRefreshQueued = true;
      missionIndexRefreshQueuedQuiet = false;
      missionIndexRefreshQueuedReason = reason || 'queued';
    }
    return true;
  }
  const now = Date.now();
  if (now - missionAutoRefreshLastAt < MISSION_AUTO_REFRESH_MIN_GAP_MS) return false;
  if (missionRefreshDebounceTimer) window.clearTimeout(missionRefreshDebounceTimer);
  missionRefreshDebounceTimer = window.setTimeout(() => {
    missionRefreshDebounceTimer = 0;
    if (!shouldWatchMissionFinishedRefresh()) return;
    if (missionIndexRefreshPending) {
      if (!quiet) {
        missionIndexRefreshQueued = true;
        missionIndexRefreshQueuedQuiet = false;
        missionIndexRefreshQueuedReason = reason || 'queued';
      }
      return;
    }
    missionAutoRefreshLastAt = Date.now();
    refreshMissionIndexClick(reason || 'watch', { quiet });
  }, Math.max(0, Number(delayMs) || 0));
  return true;
}

function scheduleMissionFinishedAutoRefresh() {
  if (missionFinishedRefreshTimer) return;
  if (!shouldWatchMissionFinishedRefresh()) return;
  if (!activeMissionRows().some((row) => rowHasActiveTrace(row) || rowHasStaleActiveTurn(row))) return;
  missionFinishedRefreshTimer = window.setTimeout(() => {
    missionFinishedRefreshTimer = 0;
    maybeRefreshFinishedThreads();
  }, MISSION_AUTO_REFRESH_TICK_MS);
}

function maybeRefreshFinishedThreads() {
  if (!shouldWatchMissionFinishedRefresh()) return;
  const rows = activeMissionRows();
  const liveRows = rows.filter((row) => rowHasActiveTrace(row));
  const staleActiveRows = rows.filter((row) => rowHasStaleActiveTurn(row));
  if (!liveRows.length && !staleActiveRows.length) return;
  if (missionIndexRefreshPending) {
    scheduleMissionFinishedAutoRefresh();
    return;
  }
  const now = Date.now();
  if (now - missionAutoRefreshLastAt < MISSION_AUTO_REFRESH_MIN_GAP_MS) {
    scheduleMissionFinishedAutoRefresh();
    return;
  }
  const generatedAt = parseTimestamp(missionIndex?.generated_at);
  const indexAgeMs = generatedAt ? now - generatedAt.getTime() : Number.POSITIVE_INFINITY;
  const quietRows = liveRows.filter((row) => {
    const last = _missionLastActivityMs(row);
    return last && now - last >= MISSION_THREAD_QUIET_REFRESH_MS;
  });
  if (staleActiveRows.length || quietRows.length || indexAgeMs >= MISSION_THREAD_QUIET_REFRESH_MS * 2) {
    const reason = staleActiveRows.length ? 'stale_active_summary_check' : 'thread_finished_check';
    const triggerRows = staleActiveRows.length ? staleActiveRows : (quietRows.length ? quietRows : liveRows);
    if (!unseenMissionAutoRefreshRows(triggerRows, reason).length) {
      scheduleMissionFinishedAutoRefresh();
      return;
    }
    scheduleMissionRefresh(reason, { quiet: true, delayMs: 0 });
    return;
  }
  scheduleMissionFinishedAutoRefresh();
}

function scheduleFocusMissionRefresh(reason) {
  if (!missionIndex || !shouldWatchMissionFinishedRefresh()) return;
  const now = Date.now();
  if (now - missionFocusRefreshLastAt < MISSION_FOCUS_REFRESH_MIN_GAP_MS) return;
  missionFocusRefreshLastAt = now;
  requestMissionIndex(reason || 'focus_title_authority_check');
}

function clearMissionTitleAuthoritySync() {
  if (missionTitleAuthoritySyncTimer) {
    window.clearTimeout(missionTitleAuthoritySyncTimer);
    missionTitleAuthoritySyncTimer = 0;
  }
}

function scheduleMissionTitleAuthoritySync(reason = 'title_authority_watch') {
  clearMissionTitleAuthoritySync();
  if (!shouldWatchMissionFinishedRefresh()) return false;
  missionTitleAuthoritySyncTimer = window.setTimeout(() => {
    missionTitleAuthoritySyncTimer = 0;
    if (!shouldWatchMissionFinishedRefresh()) return;
    requestMissionIndex(reason);
    scheduleMissionTitleAuthoritySync(reason);
  }, MISSION_TITLE_AUTHORITY_SYNC_MS);
  return true;
}

function sortedMissionRows(rows, mode = dropdownSortMode) {
  const list = Array.isArray(rows) ? rows.slice() : [];
  const retiredDelta = (a, b) => Number(rowIsOldPrefixRetired(a)) - Number(rowIsOldPrefixRetired(b));
  const attention = (row) => missionAttentionForRow(row, Date.now());
  const attentionDelta = (a, b) => (attention(b).attention_score || 0) - (attention(a).attention_score || 0);
  const timeDelta = (a, b) => _missionSortTime(b) - _missionSortTime(a);
  const goalDelta = (a, b) => missionGoalSortPriority(b) - missionGoalSortPriority(a);
  if (mode === 'dynamic') {
    // Default "most useful first": one flat list tiered by why-look-now (live
    // fleet on top), then most-recently-active within each tier. No lane headers
    // — this is a relevance ranking, not the grouped Review queue.
    return list.sort((a, b) => {
      const retired = retiredDelta(a, b);
      if (retired) return retired;
      const tierDelta = missionDynamicTier(attention(b)) - missionDynamicTier(attention(a));
      if (tierDelta) return tierDelta;
      const changed = timeDelta(a, b);
      if (changed) return changed;
      const goal = goalDelta(a, b);
      if (goal) return goal;
      return (b.mission_ordinal_key || 0) - (a.mission_ordinal_key || 0);
    });
  }
  if (mode === 'review_first') {
    return list.sort((a, b) => {
      const retired = retiredDelta(a, b);
      if (retired) return retired;
      const markerDelta = Number(Boolean(attention(b).operator_marker?.pinned)) - Number(Boolean(attention(a).operator_marker?.pinned));
      if (markerDelta) return markerDelta;
      const reviewDelta = attentionDelta(a, b);
      if (reviewDelta) return reviewDelta;
      const changed = timeDelta(a, b);
      if (changed) return changed;
      const goal = goalDelta(a, b);
      if (goal) return goal;
      return (b.mission_ordinal_key || 0) - (a.mission_ordinal_key || 0);
    });
  }
  if (mode === 'running_monitor' || mode === 'active_first') {
    return list.sort((a, b) => {
      const retired = retiredDelta(a, b);
      if (retired) return retired;
      const rogueDelta = Number(attention(b).lane === 'rogue_active') - Number(attention(a).lane === 'rogue_active');
      if (rogueDelta) return rogueDelta;
      const activeDelta = Number(rowIsLiveMission(b)) - Number(rowIsLiveMission(a));
      if (activeDelta) return activeDelta;
      const changed = timeDelta(a, b);
      if (changed) return changed;
      const goal = goalDelta(a, b);
      if (goal) return goal;
      return (b.mission_ordinal_key || 0) - (a.mission_ordinal_key || 0);
    });
  }
  if (mode === 'changed_desc' || mode === 'finished_at_desc') {
    return list.sort((a, b) => {
      const retired = retiredDelta(a, b);
      if (retired) return retired;
      const changed = timeDelta(a, b);
      if (changed) return changed;
      const goal = goalDelta(a, b);
      if (goal) return goal;
      return (b.mission_ordinal_key || 0) - (a.mission_ordinal_key || 0);
    });
  }
  if (mode === 'needs_copy') {
    return list.sort((a, b) => {
      const retired = retiredDelta(a, b);
      if (retired) return retired;
      const readyDelta = Number(attention(b).lane === 'ready_to_copy' || attention(b).attention_state === 'copy_ready') - Number(attention(a).lane === 'ready_to_copy' || attention(a).attention_state === 'copy_ready');
      if (readyDelta) return readyDelta;
      const reviewDelta = attentionDelta(a, b);
      if (reviewDelta) return reviewDelta;
      return timeDelta(a, b);
    });
  }
  if (mode === 'stale_risky') {
    return list.sort((a, b) => {
      const retired = retiredDelta(a, b);
      if (retired) return retired;
      const riskWeight = (item) => ({ red: 3, amber: 2, green: 1 }[attention(item).risk_state] || 0);
      const riskDelta = riskWeight(b) - riskWeight(a);
      if (riskDelta) return riskDelta;
      const reviewDelta = attentionDelta(a, b);
      if (reviewDelta) return reviewDelta;
      return timeDelta(a, b);
    });
  }
  if (mode === 'old_inactive') {
    return list.sort((a, b) => {
      const inactiveDelta = Number(missionRowVisibilityState(b) !== 'recent') - Number(missionRowVisibilityState(a) !== 'recent');
      if (inactiveDelta) return inactiveDelta;
      const retired = retiredDelta(a, b);
      if (retired) return retired;
      return timeDelta(a, b);
    });
  }
  if (mode === 'ordinal_desc') {
    return list.sort((a, b) => {
      const retired = retiredDelta(a, b);
      if (retired) return retired;
      const ordinalDelta = (b.mission_ordinal_key || 0) - (a.mission_ordinal_key || 0);
      if (ordinalDelta) return ordinalDelta;
      const activeDelta = Number(rowIsLiveMission(b)) - Number(rowIsLiveMission(a));
      if (activeDelta) return activeDelta;
      const changed = timeDelta(a, b);
      if (changed) return changed;
      const goal = goalDelta(a, b);
      if (goal) return goal;
      return 0;
    });
  }
  return sortedMissionRows(list, 'dynamic');
}

function findMissionByKey(key) {
  return allMissionRows().find((row) => missionKey(row) === key) || null;
}

function providerBadge(provider) {
  return providerLabel(provider);
}

function renderMissionRail() {
  if (!missionRailEl) return;
  const rows = sortedMissionRows(visibleMissionRows());
  if (!rows.length) {
    missionRailEl.textContent = missionIndex
      ? `No active missions (hidden_old=${missionIndex.hidden_old_count || 0}, inactive=${missionIndex.inactive_count || 0})`
      : 'Missions loading…';
    if (selectedMissionEl) selectedMissionEl.textContent = 'no mission selected';
    [copyCompressedBtn, copyFullBtn, revealMissionBtn].forEach((b) => { if (b) b.disabled = true; });
    return;
  }
  ensureSelectedMission(rows);
  missionRailEl.replaceChildren();
  const railRenderStart = Date.now();
  for (const row of rows.slice(0, 14)) {
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'mission-chip';
    btn.dataset.missionKey = missionKey(row);
    btn.setAttribute('role', 'tab');
    const isSelected = missionKey(row) === selectedMissionKey;
    btn.setAttribute('aria-selected', isSelected ? 'true' : 'false');
    // Same three-layer view state painted on the chips. aria-selected stays
    // semantically tied to active-tab; lifecycle layers go on data-* + glyph.
    const view = missionViewStateForRow(row, railRenderStart);
    const chipGlyph = missionViewStateGlyph(view);
    btn.dataset.activity = view.activity;
    btn.dataset.novelty = view.novelty;
    btn.dataset.copy = view.copy;
    btn.dataset.goalStatus = missionGoalStatus(row);
    const lifeNote = chipGlyph.title ? ` · ${chipGlyph.title}` : '';
    const goalNote = missionGoalOperatorText(row);
    btn.title = `${providerLabel(row.provider)} · ${missionDisplayTitle(row, activityDisplayTurn(row))} · ${shortSessionId(row.session_id)}${lifeNote}${goalNote ? ` · ${goalNote}` : ''}`;
    const badge = document.createElement('span');
    badge.className = 'badge';
    badge.textContent = providerShortBadge(row.provider);
    const stateGlyph = document.createElement('span');
    stateGlyph.className = 'chip-state-glyph';
    stateGlyph.setAttribute('aria-hidden', 'true');
    stateGlyph.textContent = chipGlyph.glyph;
    const label = document.createElement('span');
    label.className = 'label';
    label.textContent = missionDisplayTitle(row, activityDisplayTurn(row)) || '?';
    btn.appendChild(badge);
    btn.appendChild(stateGlyph);
    btn.appendChild(label);
    btn.addEventListener('click', () => selectMission(missionKey(row)));
    missionRailEl.appendChild(btn);
  }
  if (rows.length > 14) {
    const more = document.createElement('span');
    more.className = 'mission-rail-overflow';
    more.textContent = `+${rows.length - 14}`;
    missionRailEl.appendChild(more);
  }
  renderSelectedMission();
}

function renderSelectedMission() {
  if (!selectedMissionEl) return;
  const row = findMissionByKey(selectedMissionKey);
  if (!row) {
    selectedMissionEl.textContent = 'no mission selected';
    [copyCompressedBtn, copyFullBtn, revealMissionBtn].forEach((b) => { if (b) b.disabled = true; });
    if (copyCompressedBtn) copyCompressedBtn.textContent = 'Copy Latest Trace';
    return;
  }
  const refs = row.artifact_refs || {};
  const lct = activityDisplayTurn(row);
  const activeTrace = rowHasActiveTrace(row);
  const freshness = (row.artifact_freshness || {}).state || 'unknown';
  selectedMissionEl.textContent = selectedMissionOperatorSentence(row);
  // Primary button label adapts to freshness state. The native bridge
  // copyLatestMissionTrace handles the capture-then-copy combo so the
  // operator never has a disabled-with-no-explanation grey button.
  if (copyCompressedBtn) {
    const sourceWindow = selectedTraceSourceWindow();
    const stateModel = missionStateModel(row, sourceWindow);
    const visibleIndexRefresh = traceCopyRequiresVisibleIndexRefresh(row, sourceWindow, activeTrace, stateModel);
    copyCompressedBtn.disabled = false;
    if (visibleIndexRefresh) {
      copyCompressedBtn.textContent = 'Refresh Trace List';
    } else if (freshness === 'current') {
      copyCompressedBtn.textContent = activeTrace ? 'Copy Current Trace' : 'Copy Latest Trace';
    } else if (freshness === 'stale') {
      copyCompressedBtn.textContent = activeTrace ? 'Refresh + Copy Current Trace' : 'Refresh + Copy Latest Trace';
    } else if (freshness === 'partial_only') {
      copyCompressedBtn.textContent = activeTrace ? 'Copy Current Trace' : 'No Completed Turn';
      copyCompressedBtn.disabled = !activeTrace;
    } else {
      copyCompressedBtn.textContent = activeTrace ? 'Prepare + Copy Current Trace' : 'Prepare + Copy Latest Trace';
    }
  }
  if (copyFullBtn) copyFullBtn.disabled = !refs.full;
  if (revealMissionBtn) revealMissionBtn.disabled = !(refs.export || refs.compressed || refs.parsed || refs.full);
}

function selectMission(key) {
  clearPendingMissionCopyAnchor();
  selectedMissionKey = key;
  rememberSelectedMissionAnchor();
  renderMissionRail();
}

function copySelectedMissionArtifact(kind, variant) {
  return guardAgentTraceAction('copy_selected_mission', () => copySelectedMissionArtifactUnsafe(kind, variant));
}

function copySelectedMissionArtifactUnsafe(kind, variant) {
  const row = findMissionByKey(selectedMissionKey);
  if (!row) {
    setMissionBarStatus('No mission selected.');
    return;
  }
  const freshness = (row.artifact_freshness || {}).state || 'unknown';
  if (kind === 'compressed') {
    const provider = row.provider === 'claude_code' ? 'claude' : row.provider;
    const smokeTurn = Number(window.__aiwTraceSmokeTurnIndex);
    const hasForcedTurn = Number.isInteger(smokeTurn) && smokeTurn > 0;
    const traceTurn = rowHasActiveTrace(row) ? activityDisplayTurn(row) : traceDisplayTurn(row);
    const activeTrace = rowHasActiveTrace(row);
    const sourceWindow = selectedTraceSourceWindow();
    const backendSourceWindow = backendTraceSourceWindow(sourceWindow);
    const traceWindow = traceWindowForSource(row, sourceWindow, traceTurn);
    const turnIndex = hasForcedTurn
      ? smokeTurn
      : (backendSourceWindow === SOURCE_WINDOW_SELECTED_TURN ? traceTurn?.turn_index : (traceWindow.end_turn_index ?? traceTurn?.turn_index ?? null));
    const turnId = hasForcedTurn
      ? ''
      : (backendSourceWindow === SOURCE_WINDOW_SELECTED_TURN ? (traceTurn?.turn_id || '') : (traceWindow.turn_id || traceTurn?.trace_window_turn_id || traceTurn?.turn_id || ''));
    const promptSha16 = hasForcedTurn
      ? ''
      : (backendSourceWindow === SOURCE_WINDOW_SELECTED_TURN
        ? (traceTurn?.prompt_sha16 || '')
        : (backendSourceWindow === SOURCE_WINDOW_FULL_THREAD
          ? (traceWindow.prompt_sha16 || traceTurn?.full_thread_prompt_sha16 || '')
          : (traceWindow.prompt_sha16 || traceTurn?.trace_window_prompt_sha16 || traceTurn?.prompt_sha16 || '')));
    const requestedVariant = variant || tracePrimaryVariantForSource(sourceWindow);
    const stateModel = missionStateModel(row, sourceWindow);
    const readiness = stateModel.copy_readiness || {};
    const sourceLatestFallback = traceCopyCanUseSourceLatestFallback(row, sourceWindow, activeTrace, stateModel);
    if (readiness.state === 'red') {
      const why = [
        ...(readiness.blockers || []),
        stateModel.type_b_handoff_lint?.required_no_edit_language
          ? `Type B no-edit language: ${stateModel.type_b_handoff_lint.required_no_edit_language}`
          : '',
      ].filter(Boolean).join(' · ');
      setMissionBarStatus(`Trace copy blocked: ${why || 'copy readiness red'}`, { timeoutMs: 45000 });
      rememberMissionCopyFailure(missionKey(row), why || 'copy_readiness_red');
      return;
    }
    if (traceCopyRequiresVisibleIndexRefresh(row, sourceWindow, activeTrace, stateModel)) {
      const source = stateModel.source_freshness || {};
      const visibleTurn = turnIndex != null ? `visible turn #${turnIndex}` : 'visible indexed turn';
      const currentLatest = _numberOrNull(source.current_latest_turn_index);
      const currentText = currentLatest != null ? `; source latest is #${currentLatest}` : '';
      const message = `Source changed since this mission row was rendered (${visibleTurn}${currentText}). Refreshing the trace list first; copy again after the row shows the current turn.`;
      rememberMissionCopyFailure(missionKey(row), 'source_index_stale_refresh_required_before_copy');
      refreshMissionIndexClick('source_index_stale_before_copy');
      setMissionReceipt(`✗ ${message}`, 'copy_error');
      return;
    }
    const useSourceLatestIdentity = !hasForcedTurn && (sourceLatestFallback || traceCopyNeedsSourceLatest(row, sourceWindow, activeTrace, stateModel));
    const payloadPromptSha16 = useSourceLatestIdentity ? '' : promptSha16;
    const payloadTurnIndex = useSourceLatestIdentity ? null : turnIndex;
    const payloadTurnId = useSourceLatestIdentity ? '' : turnId;
    const sourceIdentityMode = useSourceLatestIdentity
      ? (activeTrace ? 'active_source_latest' : 'stale_index_source_latest')
      : 'selected_index';
    const copyMeta = missionCopyMetadata(row, sourceWindow, traceTurn, traceWindow, requestedVariant, turnIndex);
    copyMeta.copyReadinessState = readiness.state || 'unknown';
    copyMeta.typeBLintResult = stateModel.type_b_handoff_lint?.result || 'unknown';
    copyMeta.diffReconcilerStatus = stateModel.diff_reconciler?.status || 'unknown';
    copyMeta.sourceIdentityMode = sourceIdentityMode;
    copyMeta.sourceLatestFallback = sourceLatestFallback;
    copyMeta.sourceLatestFloorTurnIndex = useSourceLatestIdentity ? turnIndex : null;
    const copyAnchor = {
      ...(missionAnchor(row) || {}),
      ...copyMeta,
      prompt_sha16: payloadPromptSha16 || promptSha16,
      turn_index: payloadTurnIndex ?? turnIndex,
      turn_id: payloadTurnId || turnId,
      requested_prompt_sha16: promptSha16,
      requested_turn_index: turnIndex,
      source_identity_mode: sourceIdentityMode,
      window_start_turn_index: hasForcedTurn ? null : (backendSourceWindow === SOURCE_WINDOW_SELECTED_TURN ? traceTurn?.turn_index : (traceWindow.start_turn_index ?? traceTurn?.turn_index ?? null)),
      window_turn_count: hasForcedTurn ? 1 : (backendSourceWindow === SOURCE_WINDOW_SELECTED_TURN ? 1 : (traceWindow.turn_count || (backendSourceWindow === SOURCE_WINDOW_FULL_THREAD ? traceTurn?.full_thread_turn_count : traceTurn?.trace_window_turn_count) || 1)),
    };
    selectedMissionAnchor = copyAnchor;
    holdPendingMissionCopyAnchor(copyAnchor);
    // Mark copy intent BEFORE postNative so a 'copying' shimmer can paint
    // while the native pasteboard write is in flight. Success/failure are
    // recorded by the agentTraceStructurerMissionLatestCopy callback below.
    rememberMissionCopyStart(copyAnchor?.key, copyMeta);
    const payload = {
      provider,
      session_id: row.session_id,
      mission_key: copyAnchor?.key || selectedMissionKey,
      ui_provider: row.provider || '',
      kind: 'compressed',
      // Swift slices the lossless clip into the one operator-facing capsule.
      variant: requestedVariant,
      title: missionDisplayTitle(row, traceTurn),
      prompt_sha16: payloadPromptSha16,
      turn_index: payloadTurnIndex,
      turn_id: payloadTurnId,
      expected_prompt_sha16: payloadPromptSha16,
      expected_turn_index: payloadTurnIndex,
      expected_turn_id: payloadTurnId,
      stale_index_prompt_sha16: promptSha16,
      stale_index_turn_index: turnIndex,
      stale_index_turn_id: turnId,
      source_identity_mode: sourceIdentityMode,
      window_start_turn_index: hasForcedTurn ? null : (backendSourceWindow === SOURCE_WINDOW_SELECTED_TURN ? traceTurn?.turn_index : (traceWindow.start_turn_index ?? traceTurn?.turn_index ?? null)),
      window_turn_count: hasForcedTurn ? 1 : (backendSourceWindow === SOURCE_WINDOW_SELECTED_TURN ? 1 : (traceWindow.turn_count || (backendSourceWindow === SOURCE_WINDOW_FULL_THREAD ? traceTurn?.full_thread_turn_count : traceTurn?.trace_window_turn_count) || 1)),
      force_turn_index: hasForcedTurn,
      use_active_turn: !hasForcedTurn && activeTrace,
      allow_partial: activeTrace || hasForcedTurn,
      source_window: backendSourceWindow,
      ui_source_window: sourceWindow,
      ...traceIdentityPolicy(row, activeTrace),
      copy_readiness: stateModel.copy_readiness,
      diff_reconciler: stateModel.diff_reconciler,
      agent_episode_graph: stateModel.agent_episode_graph,
      evidence_tier: stateModel.evidence_tier,
      type_b_handoff_lint: stateModel.type_b_handoff_lint,
      goal_rollup: stateModel.goal_rollup,
      include_closeout_report: requestedVariant === 'trace_capsule' || requestedVariant === 'closeout_report',
      include_prompt: true,
      include_source_excerpts: true,
      skip_capture_if_current: false,
    };
    if (postNative('copyLatestMissionTrace', payload)) {
      const isFreshCopy = freshness === 'current' && !isSourceIndexStale(row);
      const scope = traceScopeMetrics(row, sourceWindow, traceTurn);
      setMissionBarStatus(
        `${isFreshCopy ? 'Copying' : 'Capturing + copying'} ${scope.label} for ${providerLabel(row.provider)} ${missionDisplayTitle(row, traceTurn)}…`,
        { timeoutMs: 30000 },
      );
    } else {
      setMissionBarStatus('Mission copy requires the macOS app bridge.');
    }
    return;
  }
  const refs = row.artifact_refs || {};
  const fieldByKind = { full: refs.full, parsed: refs.parsed };
  const path = fieldByKind[kind] || '';
  if (!path) {
    setMissionBarStatus(`No ${kind} artifact yet for ${missionDisplayTitle(row, traceDisplayTurn(row))}. Use Capture + Copy Latest first.`);
    return;
  }
  if (postNative('copyMissionArtifact', { kind, path })) {
    setMissionBarStatus(`Copying ${kind} for ${missionDisplayTitle(row, traceDisplayTurn(row))}…`, { timeoutMs: 8000 });
  } else {
    setMissionBarStatus('Mission copy requires the native bridge (macOS app).');
  }
}

function revealSelectedMission() {
  const row = findMissionByKey(selectedMissionKey);
  if (!row) return;
  const refs = row.artifact_refs || {};
  const path = refs.export || refs.compressed || refs.parsed || refs.full || '';
  if (!path) {
    els.status.textContent = `No artifact to reveal yet for ${missionDisplayTitle(row, traceDisplayTurn(row))}.`;
    return;
  }
  if (postNative('revealFile', { path })) {
    els.status.textContent = `Revealing ${missionDisplayTitle(row, traceDisplayTurn(row))}.`;
  } else {
    els.status.textContent = 'Reveal requires the native bridge (macOS app).';
  }
}

window.agentTraceStructurerMissionIndex = (data) => {
  const wasRefreshPending = missionIndexRefreshPending;
  lastMissionIndexEnvelope = data || null;
  if (!data || !data.ok || !data.index) {
    if (!missionIndex && missionRailEl) missionRailEl.textContent = data?.error || 'mission_index.json not found';
    if (wasRefreshPending) {
      finishMissionIndexRefresh(data);
    } else {
      maybeAutoRefreshMissionIndex('missing_or_unreadable');
    }
    if (missionIndexRefreshQueued && !missionIndexRefreshPending) {
      const queuedReason = missionIndexRefreshQueuedReason || 'queued';
      const queuedQuiet = missionIndexRefreshQueuedQuiet;
      missionIndexRefreshQueued = false;
      missionIndexRefreshQueuedQuiet = false;
      missionIndexRefreshQueuedReason = '';
      window.setTimeout(() => refreshMissionIndexClick(queuedReason, { quiet: queuedQuiet }), 0);
    }
    return;
  }
  const viewState = captureMissionListViewState();
  const previousIndexMtimeMs = _numberOrNull(missionIndex?._source_index_mtime_ms);
  missionIndex = data.index;
  if (data.mission_index_mtime_ms != null) missionIndex._source_index_mtime_ms = data.mission_index_mtime_ms;
  if (data.mission_index_mtime != null) missionIndex._source_index_mtime = data.mission_index_mtime;
  if (data.title_authority) missionIndex._title_authority = data.title_authority;
  if (data.goal_authority) missionIndex._goal_authority = data.goal_authority;
  if (data.source_activity) missionIndex._source_activity = data.source_activity;
  const currentIndexMtimeMs = _numberOrNull(missionIndex?._source_index_mtime_ms);
  hydrateVariantArtifactOverlay(missionIndex);
  observeMissionIndexUpdate(visibleMissionRows());
  pruneMissionViewState(Date.now());
  renderMissionRail();
  if (isAgentTraceWorkbenchActive()) safeRenderAgentTraceDropdown('mission_index');
  restoreMissionListViewState(viewState);
  const nativeHeavyRefreshCompleted = Boolean(data?.native_refresh_started_at || data?.native_refresh_duration_ms != null);
  if (nativeHeavyRefreshCompleted) missionAutoRefreshLastAt = Date.now();
  finishMissionIndexRefresh(data);
  const generatedAt = parseTimestamp(missionIndex.generated_at);
  const ageMs = generatedAt ? Date.now() - generatedAt.getTime() : Number.POSITIVE_INFINITY;
  if (!data.title_authority_status && (ageMs > 15000 || !activeMissionRows().length) && !missionIndexAutoRefreshTried) {
    maybeAutoRefreshMissionIndex(ageMs > 15000 ? 'stale_index' : 'empty_index');
  }
  if (missionIndexRefreshQueued && !missionIndexRefreshPending) {
    const queuedReason = missionIndexRefreshQueuedReason || 'queued';
    const queuedQuiet = missionIndexRefreshQueuedQuiet;
    missionIndexRefreshQueued = false;
    missionIndexRefreshQueuedQuiet = false;
    missionIndexRefreshQueuedReason = '';
    window.setTimeout(() => refreshMissionIndexClick(queuedReason, { quiet: queuedQuiet }), 0);
  }
  if (previousIndexMtimeMs && currentIndexMtimeMs && currentIndexMtimeMs !== previousIndexMtimeMs && isAgentTraceWorkbenchActive()) {
    setMissionReceipt(`✓ Source index changed on disk; selection restored by provider/session where possible.`);
  }
  scheduleMissionFinishedAutoRefresh();
};

window.agentTraceStructurerMissionCopy = (data) => {
  if (data?.ok) {
    const kb = Math.round((data.bytes || 0) / 1024 * 10) / 10;
    setMissionBarStatus(`✓ Copied ${data.kind} · ${kb} KB`, { timeoutMs: 8000 });
    flashScopeCopySuccess(selectedTraceSourceWindow());
  } else {
    setMissionBarStatus(`✗ Mission copy failed: ${data?.error || 'unknown'}`, { timeoutMs: 15000 });
  }
};

function requestMissionIndex(reason = 'request') {
  if (missionIndexRefreshPending) return;
  if (!postNative('requestMissionIndex', { reason, refresh_if_title_authority_changed: true })) {
    if (missionRailEl) missionRailEl.textContent = 'Loading local mission index…';
    void fetchMissionIndexHttpFallback(reason, { refresh: false });
  }
}

function refreshMissionIndexClick(reason = 'manual', opts = {}) {
  // Spawn the feeder via the Swift bridge. The native side runs
  // ./repo-python tools/meta/observability/cli_prompt_trace.py --mission-index
  // and then re-sends the updated index through agentTraceStructurerMissionIndex.
  if (missionIndexRefreshPending) {
    const queueAllowed = !opts.quiet && String(reason || 'manual') === 'manual';
    if (!queueAllowed) {
      if (!opts.quiet) {
        const elapsed = Math.max(1, Math.round((Date.now() - missionIndexRefreshStartedAt) / 1000));
        const cachedRows = Array.isArray(missionIndex?.active_rows) ? missionIndex.active_rows.length : 0;
        setMissionReceipt(`Refresh already running (${elapsed}s). Showing ${cachedRows} cached missions.`);
      }
      return;
    }
    missionIndexRefreshQueued = true;
    missionIndexRefreshQueuedQuiet = Boolean(opts.quiet);
    missionIndexRefreshQueuedReason = reason || 'queued';
    const elapsed = Math.max(1, Math.round((Date.now() - missionIndexRefreshStartedAt) / 1000));
    const cachedRows = Array.isArray(missionIndex?.active_rows) ? missionIndex.active_rows.length : 0;
    setMissionReceipt(`Refresh already running (${elapsed}s); queued one more. Showing ${cachedRows} cached missions.`);
    return;
  }
  beginMissionIndexRefresh(reason, opts);
  if (postNative('refreshMissionIndex', { reason, quiet: Boolean(opts.quiet) })) {
    els.status.textContent = 'Refreshing missions…';
  } else {
    els.status.textContent = 'Refreshing local mission index…';
    void fetchMissionIndexHttpFallback(reason, { refresh: true });
  }
}

function maybeAutoRefreshMissionIndex(reason) {
  if (missionIndexAutoRefreshTried) return;
  missionIndexAutoRefreshTried = true;
  refreshMissionIndexClick(reason);
}

function copyLatestClipboardClip() {
  if (postNative('copyLatestClipboardClip')) {
    setMissionBarStatus('Copying latest clip…', { timeoutMs: 6000 });
  } else {
    setMissionBarStatus('Latest clip copy requires the macOS app bridge.');
  }
}

window.agentTraceStructurerLatestClipCopy = (data) => {
  if (data?.ok) {
    const kb = Math.round((data.copied_bytes || 0) / 1024 * 10) / 10;
    const bits = [
      `✓ Copied latest clip`,
      data.row_kind ? `(${data.row_kind})` : '',
      `${kb} KB`,
      data.filename ? `· ${data.filename.replace(/^clip-/, '').slice(0, 32)}` : '',
    ].filter(Boolean);
    setMissionBarStatus(bits.join(' · '), { timeoutMs: 10000 });
  } else {
    const reason = data?.error || 'unknown';
    const stage = data?.stage ? ` [${data.stage}]` : '';
    setMissionBarStatus(`✗ Latest clip copy failed${stage}: ${reason}`, { timeoutMs: 15000 });
  }
};

function missionLatestCopyFailureReason(data, fallback = 'capture/copy failed') {
  const parts = [];
  const stage = String(data?.stage || '').trim();
  const error = String(data?.error || fallback || 'capture/copy failed').trim();
  if (stage) parts.push(stage);
  if (error) parts.push(error);
  const expectedTurn = data?.expected_turn_index ?? null;
  const actualTurn = data?.actual_turn_index ?? null;
  if (expectedTurn != null || actualTurn != null) {
    parts.push(`turn expected=${expectedTurn ?? 'unknown'} actual=${actualTurn ?? 'unknown'}`);
  }
  const staleFloorTurn = data?.stale_index_turn_index ?? null;
  if (staleFloorTurn != null) {
    parts.push(`source latest floor turn>=${staleFloorTurn}`);
  }
  const expectedPrompt = String(data?.expected_prompt_sha16 || '').trim();
  const actualPrompt = String(data?.actual_prompt_sha16 || '').trim();
  if (expectedPrompt || actualPrompt) {
    const expected = expectedPrompt ? expectedPrompt.slice(0, 8) : 'unknown';
    const actual = actualPrompt ? actualPrompt.slice(0, 8) : 'unknown';
    parts.push(`prompt expected=${expected} actual=${actual}`);
  }
  const mode = String(data?.source_identity_mode || '').trim();
  if (mode) parts.push(`identity=${mode}`);
  return parts.filter(Boolean).join(' · ') || fallback;
}

function captureSelectedMissionTrace() {
  const row = findMissionByKey(selectedMissionKey);
  if (!row) {
    els.status.textContent = 'No mission selected.';
    return;
  }
  // Provider mapping: claude_code -> claude (cli_prompt_trace --provider arg)
  const provider = row.provider === 'claude_code' ? 'claude' : row.provider;
  const payload = {
    provider,
    session_id: row.session_id,
    without_prompt: true,
  };
  if (postNative('captureMissionTrace', payload)) {
    els.status.textContent = `Capturing latest trace for ${missionDisplayTitle(row, traceDisplayTurn(row))}…`;
  } else {
    els.status.textContent = 'Capture requires the macOS app bridge.';
  }
}

window.agentTraceStructurerMissionCapture = (data) => {
  if (data?.ok) {
    els.status.textContent = `Captured ${data.title || 'mission'} trace (${data.bytes || 0} bytes).`;
    // Refresh so artifact_refs populate.
    refreshMissionIndexClick();
  } else {
    els.status.textContent = `Capture failed: ${data?.error || 'unknown'}`;
  }
};

window.agentTraceStructurerMissionLatestCopy = (data) => {
  if (data?.ok) {
    const bits = [
      `✓ Copied ${data.freshness || 'latest'} trace`,
      data.title || data.session_id || '',
    ];
    if (data.turn_index != null) bits.push(`turn #${data.turn_index}`);
    if (data.prompt_sha16) bits.push(`prompt ${data.prompt_sha16.slice(0, 8)}`);
    if (data.copied_bytes) bits.push(`${Math.round(data.copied_bytes / 1024 * 10) / 10} KB`);
    setMissionBarStatus(bits.join(' · '), { timeoutMs: 10000 });
    flashScopeCopySuccess(selectedTraceSourceWindow());
    // Refresh so the chip reflects the new artifact + freshness state.
    refreshMissionIndexClick();
  } else {
    setMissionBarStatus(`✗ Capture+copy failed: ${missionLatestCopyFailureReason(data, 'unknown')}`, { timeoutMs: 15000 });
  }
};
let clipboardSignalUntil = 0;
let operatorHudOpening = false;
let reinstallInFlight = false;
let reinstallRequestId = '';
let reinstallReceiptTimeout = 0;
let reinstallRelaunchTimeout = 0;
let latestRevealPending = false;
let latestRevealTimeout = 0;
let latestCapturePromise = Promise.resolve();
let clipboardCaptureSerial = 0;
const CAPTURE_HISTORY_MEMORY_LIMIT = 50;
const CAPTURE_HISTORY_DISPLAY_LIMIT = 20;
const RECENT_CAPTURE_RETENTION_LIMIT = 10;
const SYSTEM_BAR_COLLAPSE_DELAY_MS = 420;
const SYSTEM_BAR_COMPACT_HOVER_OPEN_MS = 180;
const SYSTEM_BAR_DRAG_THRESHOLD_PX = 5;
const SIGNAL_FLASH_MS = 1600;
const SIGNAL_GREEN_HOLD_MS = 60000;
const SIGNAL_DECAY_AFTER_HOLD_MS = 120000;
const SIGNAL_FIRST_MINUTE_AMBER_RATIO = 0.15;
const SIGNAL_IDLE_RGB = [123, 134, 117];
const SIGNAL_GREEN_RGB = [116, 198, 157];
const SIGNAL_AMBER_RGB = [199, 176, 106];
const NATIVE_STORE_PAYLOAD_LIMIT_BYTES = 8 * 1024 * 1024;
const REINSTALL_RECEIPT_TIMEOUT_MS = 12000;
const REINSTALL_RELAUNCH_TIMEOUT_MS = 45000;

function fmt(value) {
  return Number(value || 0).toLocaleString();
}

function byteLength(value) {
  return new TextEncoder().encode(String(value || '')).length;
}

function truncateText(value, maxChars = 240) {
  const text = String(value || '');
  if (text.length <= maxChars) return text;
  return `${text.slice(0, Math.max(0, maxChars - 34))}\n[preview only: ${text.length - maxChars + 34} chars omitted]`;
}

function attachmentSidecars(packet, clip) {
  if (clip.carrier_mode !== 'raw_sidecar_plus_index') return [];
  const filename = clip.raw_sidecar?.filename || 'clip.raw.txt';
  return [{
    filename,
    content: packet.source_text || '',
    role: 'exact_clip_source',
  }];
}

function attachmentClipPayload(packet, refs = {}) {
  const clip = buildAttachmentClip(packet, {
    retention_limit: RECENT_CAPTURE_RETENTION_LIMIT,
    ...refs,
  });
  const jsonText = JSON.stringify(clip);
  const sidecars = attachmentSidecars(packet, clip);
  return {
    packet: clip,
    jsonText,
    bytes: byteLength(jsonText),
    sidecars,
    bundleBytes: byteLength(jsonText) + sidecars.reduce((sum, sidecar) => sum + byteLength(sidecar.content), 0),
  };
}

function formatBytes(value) {
  const bytes = Number(value || 0);
  if (!Number.isFinite(bytes) || bytes <= 0) return '0 bytes';
  if (bytes < 1024) return `${bytes} ${bytes === 1 ? 'byte' : 'bytes'}`;
  const kb = bytes / 1024;
  if (kb < 1000) return `${kb < 10 ? kb.toFixed(1) : Math.round(kb)} KB`;
  return `${(kb / 1024).toFixed(1)} MB`;
}

function timestampMs(value) {
  if (value == null || value === '') return null;
  if (typeof value === 'number' && Number.isFinite(value)) {
    // Provider rows may carry unix milliseconds; older sidecars sometimes
    // carry seconds. Preserve both so activity is keyed to the thread, not the
    // selected copy artifact.
    return value > 1e12 ? value : value * 1000;
  }
  const raw = String(value || '').trim();
  if (!raw) return null;
  if (/^\d+(?:\.\d+)?$/.test(raw)) {
    const numeric = Number(raw);
    if (Number.isFinite(numeric)) return numeric > 1e12 ? numeric : numeric * 1000;
  }
  const normalized = /(?:Z|[+-]\d{2}:?\d{2})$/i.test(raw) ? raw : `${raw}Z`;
  const ms = Date.parse(normalized);
  return Number.isFinite(ms) ? ms : null;
}

function parseTimestamp(value) {
  const ms = timestampMs(value);
  return ms == null ? null : new Date(ms);
}

function formatClockLabel(value) {
  const date = parseTimestamp(value);
  if (!date) return '';
  try {
    return new Intl.DateTimeFormat(undefined, {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false,
      timeZoneName: 'short',
    }).format(date);
  } catch (_) {
    return date.toLocaleTimeString();
  }
}

function ageLabel(value) {
  const date = parseTimestamp(value);
  if (!date) return 'now';
  const seconds = Math.max(0, Math.floor((Date.now() - date.getTime()) / 1000));
  if (seconds < 10) return 'now';
  if (seconds < 60) return `${seconds} seconds ago`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes} ${minutes === 1 ? 'minute' : 'minutes'} ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours} ${hours === 1 ? 'hour' : 'hours'} ago`;
  const days = Math.floor(hours / 24);
  return `${days} ${days === 1 ? 'day' : 'days'} ago`;
}

function compactAgeLabel(value) {
  const date = parseTimestamp(value);
  if (!date) return '—';
  const seconds = Math.max(0, Math.floor((Date.now() - date.getTime()) / 1000));
  if (seconds < 10) return 'now';
  if (seconds < 60) return `${seconds}s ago`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

function exactTimeLabel(value) {
  return formatClockLabel(value) || String(value || '');
}

function copiedTurnFinishAgeLabel(completedAt, now = Date.now()) {
  const completedMs = timestampMs(completedAt);
  if (completedMs == null) return '';
  const minutes = Math.max(0, Math.floor((now - completedMs) / 60000));
  if (minutes < 1) return 'finished less than 1 minute ago';
  return `finished ${minutes} ${minutes === 1 ? 'minute' : 'minutes'} ago`;
}

function missionCopyMetadata(row, sourceWindow, traceTurn, traceWindow, variant, turnIndex) {
  const normalizedSource = normalizeTraceSourceWindow(sourceWindow);
  const copiedTurnIndex = turnIndex ?? traceWindow?.end_turn_index ?? traceTurn?.turn_index ?? null;
  return {
    copiedSourceWindow: normalizedSource,
    copiedVariantLabel: tracePrimaryVariantLabel(variant || tracePrimaryVariantForSource(normalizedSource), normalizedSource),
    copiedSourceWindowLabel: traceSourceWindowLabel(normalizedSource),
    copiedRangeLabel: traceSourceWindowRangeLabel(row, normalizedSource, traceTurn),
    copiedTurnIndex,
    copiedTurnCompletedAt: traceTurn?.completed_at || '',
    copiedTurnStartedAt: traceTurn?.started_at || '',
    copiedTurnInFlight: traceTurnLooksActive(traceTurn),
  };
}

function missionCopySummary(entry, now = Date.now(), { includeBytes = true, includeScope = false } = {}) {
  if (!entry) return '';
  const parts = [];
  if (includeScope && entry.copiedSourceWindowLabel) parts.push(entry.copiedSourceWindowLabel);
  const rangeIsCopiedTurn = entry.copiedTurnIndex != null
    && String(entry.copiedRangeLabel || '') === `turn #${entry.copiedTurnIndex}`;
  if (includeScope && entry.copiedRangeLabel && entry.copiedRangeLabel !== entry.copiedSourceWindowLabel && !rangeIsCopiedTurn) {
    parts.push(entry.copiedRangeLabel);
  }
  if (entry.copiedTurnIndex != null) {
    const finish = copiedTurnFinishAgeLabel(entry.copiedTurnCompletedAt, now);
    const inFlight = entry.copiedTurnInFlight && !finish ? 'still running' : '';
    parts.push(`turn #${entry.copiedTurnIndex}${finish ? ` ${finish}` : (inFlight ? ` ${inFlight}` : '')}`);
  }
  const copiedBytes = Number(entry.copiedBytes || 0);
  if (includeBytes && Number.isFinite(copiedBytes) && copiedBytes > 0) parts.push(_formatKB(copiedBytes));
  return parts.filter(Boolean).join(' · ');
}

function markClipboardSignal() {
  clipboardSignalUntil = Date.now() + SIGNAL_FLASH_MS;
  renderTopSummary();
}

function normalizedKind(value) {
  if (!value || value === 'clipboard_text') return 'text';
  return value;
}

function formatKind(value) {
  const kind = normalizedKind(value);
  const labels = {
    agent_trace: 'Agent trace',
    code_file: 'Code file',
    command_trace: 'Command trace',
    json_like: 'JSON',
    mixed_paste: 'Mixed paste',
    operator_thread_export: 'Thread export',
    packet: 'Packet',
    prompt: 'Prompt',
    review_diff: 'Review/diff',
    source_file: 'Source file',
    text: 'Text',
  };
  return labels[kind] || kind.replaceAll('_', ' ');
}

function mixRgb(start, end, ratio) {
  return start.map((channel, index) => Math.round(channel + (end[index] - channel) * ratio));
}

function rgbToHex(rgb) {
  return `#${rgb.map((channel) => channel.toString(16).padStart(2, '0')).join('')}`;
}

function signalFreshnessRatio(ageMs) {
  const age = Math.max(0, Number(ageMs || 0));
  if (!Number.isFinite(age) || age <= 0) return 0;
  if (age <= SIGNAL_GREEN_HOLD_MS) {
    return Math.min(SIGNAL_FIRST_MINUTE_AMBER_RATIO, (age / SIGNAL_GREEN_HOLD_MS) * SIGNAL_FIRST_MINUTE_AMBER_RATIO);
  }
  const decayRatio = Math.min(1, (age - SIGNAL_GREEN_HOLD_MS) / SIGNAL_DECAY_AFTER_HOLD_MS);
  return SIGNAL_FIRST_MINUTE_AMBER_RATIO + decayRatio * (1 - SIGNAL_FIRST_MINUTE_AMBER_RATIO);
}

function signalPresentation(capture) {
  if (!capture) {
    return { state: 'idle', rgb: SIGNAL_IDLE_RGB, color: rgbToHex(SIGNAL_IDLE_RGB) };
  }
  const date = capture.capturedAt ? new Date(capture.capturedAt) : null;
  const ageMs = date && !Number.isNaN(date.getTime()) ? Math.max(0, Date.now() - date.getTime()) : 0;
  const ratio = signalFreshnessRatio(ageMs);
  const rgb = mixRgb(SIGNAL_GREEN_RGB, SIGNAL_AMBER_RGB, ratio);
  const state = Date.now() < clipboardSignalUntil
    ? 'fresh'
    : ageMs <= SIGNAL_GREEN_HOLD_MS ? 'ready' : ratio >= 1 ? 'aged' : 'aging';
  return { state, rgb, color: rgbToHex(rgb) };
}

function ensureJsonFilename(value) {
  const name = value.trim() || defaultTraceFilename();
  return name.toLowerCase().endsWith('.json') ? name : `${name}.json`;
}

function lineRange(range) {
  return range.start === range.end ? `L${range.start}` : `L${range.start}-${range.end}`;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;');
}

function matches(value, query) {
  return String(value).toLowerCase().includes(query.toLowerCase());
}

function nativeHandler(name) {
  return window.webkit?.messageHandlers?.[name] || null;
}

function hasNativeBridge(name = 'downloadJson') {
  return Boolean(nativeHandler(name));
}

function isStandaloneBrowserRuntime() {
  const localHosts = new Set(['127.0.0.1', 'localhost', '::1']);
  return !window.webkit?.messageHandlers && localHosts.has(window.location.hostname);
}

function postNative(name, payload = {}) {
  const handler = nativeHandler(name);
  if (!handler) return false;
  try {
    handler.postMessage(payload);
    return true;
  } catch (error) {
    try {
      console.error('[native post failed]', name, error);
    } catch (_) {}
    els.status.textContent = `Native bridge failed for ${name}: ${error?.message || error}`;
    return false;
  }
}

async function fetchMissionIndexHttpFallback(reason = 'request', opts = {}) {
  if (missionHttpIndexPending) return false;
  missionHttpIndexPending = true;
  const params = new URLSearchParams({ reason: String(reason || 'request') });
  if (opts.refresh) params.set('refresh', '1');
  try {
    const response = await fetch(`/mission-index?${params.toString()}`, { cache: 'no-store' });
    let payload = {};
    try {
      payload = await response.json();
    } catch (error) {
      payload = { ok: false, stage: 'http_fallback', error: `invalid mission-index response: ${error?.message || error}` };
    }
    if (!response.ok && payload && typeof payload === 'object') {
      payload.ok = false;
      payload.stage = payload.stage || 'http_fallback';
      payload.error = payload.error || `HTTP ${response.status}`;
    }
    window.agentTraceStructurerMissionIndex({
      ...(payload && typeof payload === 'object' ? payload : {}),
      http_fallback: true,
    });
    return Boolean(payload?.ok);
  } catch (error) {
    window.agentTraceStructurerMissionIndex({
      ok: false,
      stage: 'http_fallback',
      error: `local mission index unavailable: ${error?.message || error}`,
      http_fallback: true,
    });
    return false;
  } finally {
    missionHttpIndexPending = false;
  }
}

function isToolbarDragTarget(target) {
  if (!(target instanceof Element)) return false;
  return !target.closest('button,input,textarea,select,a,[role="button"],[data-no-drag]');
}

function startToolbarDrag(event) {
  if (event.button !== 0 || !hasNativeBridge('moveWindow') || !isToolbarDragTarget(event.target)) return;
  toolbarDrag = {
    pointerId: event.pointerId,
    startX: event.screenX,
    startY: event.screenY,
    x: event.screenX,
    y: event.screenY,
    moved: false,
    startedCompact: !systemBarExpanded || document.body.dataset.systembarMode === 'compact',
  };
  toolbarDragHandle?.setPointerCapture?.(event.pointerId);
  document.body.dataset.draggingToolbar = 'true';
  postNative('moveWindow', { phase: 'begin' });
  event.preventDefault();
}

function moveToolbarDrag(event) {
  if (!toolbarDrag || event.pointerId !== toolbarDrag.pointerId) return;

  const totalDx = event.screenX - toolbarDrag.startX;
  const totalDy = event.screenY - toolbarDrag.startY;
  if (!toolbarDrag.moved && Math.hypot(totalDx, totalDy) < SYSTEM_BAR_DRAG_THRESHOLD_PX) return;

  const dx = event.screenX - toolbarDrag.x;
  const dy = event.screenY - toolbarDrag.y;
  if (Math.abs(dx) + Math.abs(dy) < 1) return;

  toolbarDrag.x = event.screenX;
  toolbarDrag.y = event.screenY;
  toolbarDrag.moved = true;
  postNative('moveWindow', { phase: 'move', dx, dy });
  event.preventDefault();
}

function endToolbarDrag(event, options = {}) {
  if (!toolbarDrag) return;
  if (!options.force && event && 'pointerId' in event && event.pointerId !== toolbarDrag.pointerId) return;
  const drag = toolbarDrag;
  try {
    toolbarDragHandle?.releasePointerCapture?.(drag.pointerId);
  } catch (error) {
    // Some WKWebView builds throw if capture was already lost.
  }
  const releaseType = event?.type || '';
  toolbarDrag = null;
  if (drag.moved) lastToolbarDragEndedAt = Date.now();
  delete document.body.dataset.draggingToolbar;
  const nativePhase = releaseType === 'pointercancel' || releaseType === 'lostpointercapture' ? 'cancel' : 'end';
  postNative('moveWindow', { phase: nativePhase });
  if (!drag.moved && drag.startedCompact && (releaseType === 'pointerup' || releaseType === 'mouseup')) {
    clearSystemBarCollapseTimer();
    systemBarPinned = true;
    systemBarHover = true;
    applySystemBarMode('compact_click_release');
  }
}

function clearSystemBarCollapseTimer() {
  if (systemBarCollapseTimer) {
    window.clearTimeout(systemBarCollapseTimer);
    systemBarCollapseTimer = 0;
  }
}

function clearSystemBarCompactHoverTimer() {
  if (systemBarCompactHoverTimer) {
    window.clearTimeout(systemBarCompactHoverTimer);
    systemBarCompactHoverTimer = 0;
  }
}

function hideSystemBarContent() {
  if (systemBarRevealTimer) {
    window.clearTimeout(systemBarRevealTimer);
    systemBarRevealTimer = 0;
  }
  document.body.dataset.systembarContent = 'hidden';
}

function showSystemBarContent() {
  if (systemBarRevealTimer) {
    window.clearTimeout(systemBarRevealTimer);
    systemBarRevealTimer = 0;
  }
  document.body.dataset.systembarContent = 'visible';
}

function interactiveSystemBarTarget(target) {
  return target instanceof Element && Boolean(target.closest('button,input,textarea,select,a,[role="button"],[data-no-drag]'));
}

function applySystemBarMode(reason = '') {
  if (isWindowShellMode()) {
    systemBarPinned = true;
    systemBarHover = true;
    systemBarExpanded = true;
    document.body.dataset.systembarExpanded = 'true';
    document.body.dataset.systembarPinned = 'true';
    document.body.dataset.systembarMode = 'pinned';
    document.body.dataset.systembarContent = 'visible';
    systemBarLastMode = 'window';
    return;
  }
  // v10 sticky-workbench root-cause fix: the legacy hover/pin state
  // machine (applySystemBarMode) runs independently of the workbench
  // dropdown and posts setWindowMode('compact') whenever the operator's
  // mouse leaves the bar. That Swift handler shrinks the native window
  // to compactWindowSize (56px), bypassing closeDropdown entirely and
  // making the workbench appear to collapse on every row click that
  // briefly takes the pointer out of the bar's hover zone.
  // When the Agent Trace workbench is active, it owns the frame
  // via setSystemBarFrame; suppress the legacy mode-change side effect.
  if (isAgentTraceWorkbenchActive() && reason !== 'minimize' && reason !== 'escape') {
    // Still update DOM dataset so CSS state is coherent, but DO NOT
    // post the native setWindowMode that would shrink the window.
    const expanded = systemBarPinned || systemBarHover;
    document.body.dataset.systembarExpanded = expanded ? 'true' : 'false';
    document.body.dataset.systembarPinned = systemBarPinned ? 'true' : 'false';
    document.body.dataset.systembarMode = systemBarPinned ? 'pinned' : expanded ? 'hover' : 'compact';
    if (expanded) showSystemBarContent();
    else hideSystemBarContent();
    return;
  }
  const expanded = systemBarPinned || systemBarHover;
  const mode = expanded ? 'expanded' : 'compact';
  const modeChanged = systemBarLastMode !== mode;
  const forceNativeModePost =
    reason === 'pin' ||
    reason === 'minimize' ||
    reason === 'escape' ||
    reason === 'compact_click_release' ||
    reason === 'native_compact_click';
  const hasWindowModeBridge = hasNativeBridge('setWindowMode');
  systemBarExpanded = expanded;
  document.body.dataset.systembarExpanded = expanded ? 'true' : 'false';
  document.body.dataset.systembarPinned = systemBarPinned ? 'true' : 'false';
  document.body.dataset.systembarMode = systemBarPinned ? 'pinned' : expanded ? 'hover' : 'compact';
  if (!hasWindowModeBridge) {
    document.body.dataset.nativeWindowMode = expanded ? 'expanded' : 'compact';
    document.body.dataset.nativeShellMode = 'floating';
  }
  if (expanded) {
    showSystemBarContent();
  } else if (!expanded) {
    hideSystemBarContent();
  }
  if (modeChanged || forceNativeModePost) {
    if (hasWindowModeBridge) {
      postNative('setWindowMode', {
        mode,
        pinned: systemBarPinned,
        reason,
      });
    }
    systemBarLastMode = mode;
  }
}

function expandSystemBar(reason = 'hover') {
  clearSystemBarCollapseTimer();
  clearSystemBarCompactHoverTimer();
  systemBarHover = true;
  applySystemBarMode(reason);
}

function handleSystemBarPointerEnter() {
  clearSystemBarCollapseTimer();
  if (document.body.dataset.systembarMode === 'compact' || document.body.dataset.nativeWindowMode === 'compact') {
    clearSystemBarCompactHoverTimer();
    systemBarCompactHoverTimer = window.setTimeout(() => {
      systemBarCompactHoverTimer = 0;
      if (toolbarDrag || systemBarPinned || activeDropdown) return;
      systemBarPinned = false;
      systemBarHover = true;
      applySystemBarMode('compact_hover');
    }, SYSTEM_BAR_COMPACT_HOVER_OPEN_MS);
    return;
  }
  expandSystemBar('hover');
}

function handleSystemBarPointerLeave() {
  clearSystemBarCompactHoverTimer();
  scheduleSystemBarCollapse('leave');
}

function collapseSystemBar(reason = 'leave') {
  clearSystemBarCollapseTimer();
  clearSystemBarCompactHoverTimer();
  systemBarPinned = false;
  systemBarHover = false;
  applySystemBarMode(reason);
}

function scheduleSystemBarCollapse(reason = 'leave') {
  clearSystemBarCollapseTimer();
  clearSystemBarCompactHoverTimer();
  if (systemBarPinned || toolbarDrag || activeDropdown) return;
  systemBarCollapseTimer = window.setTimeout(() => {
    systemBarCollapseTimer = 0;
    if (systemBarPinned || toolbarDrag || activeDropdown) return;
    systemBarHover = false;
    applySystemBarMode(reason);
  }, SYSTEM_BAR_COLLAPSE_DELAY_MS);
}

function pinSystemBar(event) {
  if (interactiveSystemBarTarget(event.target)) return;
  if (Date.now() - lastToolbarDragEndedAt < 220) return;
  clearSystemBarCollapseTimer();
  clearSystemBarCompactHoverTimer();
  systemBarPinned = true;
  systemBarHover = true;
  applySystemBarMode('pin');
}

function expandSystemBarFromNativeCompactClick() {
  clearSystemBarCollapseTimer();
  clearSystemBarCompactHoverTimer();
  systemBarPinned = true;
  systemBarHover = true;
  applySystemBarMode('native_compact_click');
  return true;
}

function syncNativeWindowMode(mode, reason = 'native_sync') {
  const normalized = mode === 'window' ? 'window' : mode === 'expanded' ? 'expanded' : 'compact';
  clearSystemBarCollapseTimer();
  clearSystemBarCompactHoverTimer();
  document.body.dataset.nativeWindowMode = normalized;
  document.body.dataset.nativeShellMode = normalized === 'window' ? 'window' : 'floating';
  updateShellModeButton();
  if (normalized === 'window') {
    systemBarPinned = true;
    systemBarHover = true;
    systemBarExpanded = true;
    document.body.dataset.systembarExpanded = 'true';
    document.body.dataset.systembarPinned = 'true';
    document.body.dataset.systembarMode = 'pinned';
    document.body.dataset.systembarContent = 'visible';
    document.body.dataset.dropdownActive = activeDropdown ? 'true' : 'false';
    systemBarLastMode = 'window';
    window.setTimeout(() => ensureWindowShellWorkbench(activeDropdown || 'agent_trace'), 0);
    return true;
  }
  if (normalized === 'compact') {
    activeDropdown = null;
    if (dropdownEls?.panel) {
      dropdownEls.panel.hidden = true;
      dropdownEls.panel.dataset.mode = '';
    }
    placePromptsSurface(false);
    dropdownEls?.latestClipTrigger?.setAttribute('aria-expanded', 'false');
    dropdownEls?.agentTraceTrigger?.setAttribute('aria-expanded', 'false');
    dropdownEls?.promptsTrigger?.setAttribute('aria-expanded', 'false');
    els.buttons.operatorHud?.setAttribute('aria-expanded', 'false');
    document.body.dataset.dropdownActive = 'false';
    systemBarPinned = false;
    systemBarHover = false;
    systemBarExpanded = false;
    document.body.dataset.systembarExpanded = 'false';
    document.body.dataset.systembarPinned = 'false';
    document.body.dataset.systembarMode = 'compact';
    hideSystemBarContent();
    systemBarLastMode = 'compact';
    return true;
  }

  systemBarPinned = true;
  systemBarHover = true;
  systemBarExpanded = true;
  placePromptsSurface(false);
  document.body.dataset.systembarExpanded = 'true';
  document.body.dataset.systembarPinned = 'true';
  document.body.dataset.systembarMode = 'pinned';
  document.body.dataset.dropdownActive = activeDropdown ? 'true' : 'false';
  showSystemBarContent();
  systemBarLastMode = 'expanded';
  return true;
}

function isWindowShellMode() {
  return document.body.dataset.nativeShellMode === 'window' || document.body.dataset.nativeWindowMode === 'window';
}

function setShellMode(mode, reason = 'operator') {
  const normalized = mode === 'window' ? 'window' : 'floating';
  document.body.dataset.nativeShellMode = normalized;
  updateShellModeButton();
  if (normalized === 'window') {
    syncNativeWindowMode('window', reason);
  } else if (document.body.dataset.nativeWindowMode === 'window') {
    syncNativeWindowMode('compact', reason);
  }
  postNative('setShellMode', { mode: normalized, reason });
}

function toggleShellMode() {
  setShellMode(isWindowShellMode() ? 'floating' : 'window', 'toggle_button');
}

function zoomWindowFromToolbar(event) {
  if (!hasNativeBridge('zoomWindow') || !isToolbarDragTarget(event.target)) return;
  event.preventDefault();
  event.stopPropagation();
  postNative('zoomWindow', { source: 'toolbar_double_click' });
}

function updateShellModeButton() {
  const btn = document.getElementById('shell-mode-toggle');
  if (!btn) return;
  const windowMode = isWindowShellMode();
  btn.textContent = windowMode ? 'Float' : 'Window';
  btn.setAttribute('aria-pressed', windowMode ? 'true' : 'false');
  btn.title = windowMode
    ? 'Return to the compact floating system bar'
    : 'Open as a normal resizable macOS window';
}

function previewPacket(packet) {
  const sourceLines = Array.isArray(packet.source_lines) ? packet.source_lines : [];
  const sourceText = typeof packet.source_text === 'string' ? packet.source_text : '';
  const sourceChunks = Array.isArray(packet.source_chunks) ? packet.source_chunks : [];
  const needsLinePreview = sourceLines.length > 420;
  const needsTextPreview = sourceText.length > 2400;
  const needsChunkPreview = sourceChunks.length > 120;
  if (!needsLinePreview && !needsTextPreview && !needsChunkPreview) return packet;

  const preview = {
    ...packet,
  };
  if (needsTextPreview) {
    preview.source_text = `[preview only: ${sourceText.length} source_text chars hidden here; native private store keeps exact source_text, Copy Compressed and Download use an attachment-safe clip]`;
  }
  if (needsLinePreview) {
    preview.source_lines = [
      ...sourceLines.slice(0, 220),
      {
        line: null,
        text: `[preview only: ${packet.source_lines.length - 420} source lines omitted here; native private store keeps complete source_lines, Copy Compressed and Download use bounded samples]`,
      },
      ...sourceLines.slice(-200),
    ];
  }
  if (needsChunkPreview) {
    preview.source_chunks = [
      ...sourceChunks.slice(0, 80),
      {
        id: 'preview_omitted_source_chunks',
        title: `[preview only: ${sourceChunks.length - 120} source chunks omitted here; native private store keeps all source_chunks]`,
      },
      ...sourceChunks.slice(-40),
    ];
  }
  return preview;
}

function previewSourceSegment(segment) {
  const text = String(segment?.text || '');
  return {
    ...segment,
    text: text.length > 520 ? truncateText(text, 520) : text,
    preview_only_text_may_be_elided: text.length > 520,
  };
}

function previewClipPacket(clip) {
  const segments = Array.isArray(clip?.source_segments) ? clip.source_segments : [];
  if (!segments.length) return clip;
  const sourceBytes = Number(clip.source_integrity?.source_text_bytes || 0);
  const preview = {
    ...clip,
    ui_preview_note: 'This panel elides large source_segments for readability. Copy Compressed and Download emit the exact clip.',
  };
  if (sourceBytes <= 2400 && segments.length <= 3) {
    preview.source_segments = segments.map(previewSourceSegment);
    return preview;
  }
  const head = segments.slice(0, Math.min(2, segments.length)).map(previewSourceSegment);
  const tail = segments.length > 3 ? segments.slice(-1).map(previewSourceSegment) : [];
  preview.source_segments = [
    ...head,
    {
      id: 'preview_omitted_source_segments',
      preview_only: true,
      omitted_segment_count: Math.max(0, segments.length - head.length - tail.length),
      text: `[preview only: ${formatBytes(sourceBytes)} exact source is present in Copy Compressed/Download; source_segment_index lists every range]`,
    },
    ...tail,
  ];
  return preview;
}

function browserDownload(filename, content, type = 'application/json') {
  const blob = new Blob([content], { type });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}

function nativeDownload(filename, jsonText, sidecars = []) {
  const requestId = `download_${Date.now()}_${Math.random().toString(16).slice(2)}`;
  return new Promise((resolve, reject) => {
    pendingNativeDownloads.set(requestId, { resolve, reject });
    postNative('downloadJson', {
      request_id: requestId,
      filename,
      content: jsonText,
      sidecars,
    });
    window.setTimeout(() => {
      if (!pendingNativeDownloads.has(requestId)) return;
      pendingNativeDownloads.delete(requestId);
      reject(new Error('Native download timed out.'));
    }, 20000);
  });
}

function nativeStoreCapture(filename, jsonText, capture, exportJsonText, exportSidecars = []) {
  const requestId = `store_${Date.now()}_${Math.random().toString(16).slice(2)}`;
  return new Promise((resolve, reject) => {
    pendingNativeStores.set(requestId, { resolve, reject });
    postNative('storeCaptureJson', {
      request_id: requestId,
      filename,
      content: jsonText,
      export_content: exportJsonText,
      export_sidecars: exportSidecars,
      capture,
    });
    window.setTimeout(() => {
      if (!pendingNativeStores.has(requestId)) return;
      pendingNativeStores.delete(requestId);
      reject(new Error('Private capture store timed out.'));
    }, 20000);
  });
}

async function serverDownload(filename, jsonText) {
  const response = await fetch('/save-json', {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ filename, content: jsonText }),
  });
  if (!response.ok) throw new Error(`Save failed with HTTP ${response.status}.`);
  return response.json();
}

async function downloadJson(filename, packet, options = {}) {
  const safeName = ensureJsonFilename(filename);
  const payload = attachmentClipPayload(packet, options.refs || {});
  const jsonText = payload.jsonText;
  const artifactBytes = payload.bytes;
  const fullPacketBytes = byteLength(JSON.stringify(packet, null, 2));

  if (hasNativeBridge('downloadJson')) {
    try {
      const result = await nativeDownload(safeName, jsonText, payload.sidecars);
      if (!options.quiet) {
        els.status.textContent = payload.sidecars.length
          ? `Saved ${result.filename || safeName} plus raw sidecar to export folder.`
          : `Saved ${result.filename || safeName} to export folder.`;
      }
      return { ...result, mode: 'native', artifact_bytes: artifactBytes, clip_bytes: artifactBytes, full_packet_bytes: fullPacketBytes };
    } catch (error) {
      if (!options.quiet) els.status.textContent = `${error.message} Falling back to browser download.`;
    }
  }

  if (window.location.protocol.startsWith('http')) {
    try {
      const result = await serverDownload(safeName, jsonText);
      if (!options.quiet) els.status.textContent = `Saved ${result.filename || safeName} to Downloads.`;
      return { ...result, mode: 'server', artifact_bytes: artifactBytes, clip_bytes: artifactBytes, full_packet_bytes: fullPacketBytes };
    } catch (error) {
      if (!options.quiet) els.status.textContent = `${error.message} Falling back to browser download.`;
    }
  }

  browserDownload(safeName, jsonText);
  for (const sidecar of payload.sidecars) browserDownload(sidecar.filename, sidecar.content, 'text/plain');
  if (!options.quiet) {
    els.status.textContent = payload.sidecars.length
      ? `Browser download started for ${safeName} plus raw sidecar.`
      : `Browser download started for ${safeName}.`;
  }
  return { ok: true, filename: safeName, path: '', mode: 'browser', artifact_bytes: artifactBytes, clip_bytes: artifactBytes, full_packet_bytes: fullPacketBytes };
}

function eventClass(kind, status) {
  if (status === 'fail') return 'tone-fail';
  if (status === 'pass') return 'tone-pass';
  if (kind === 'mutation') return 'tone-warn';
  if (kind === 'commit') return 'tone-gold';
  if (kind === 'command') return 'tone-blue';
  return '';
}

function filenameStamp(iso) {
  return (iso || new Date().toISOString()).replace(/[:.]/g, '-');
}

function buildClipboardPacket(text, payload = {}) {
  const capturedAt = payload.captured_at || new Date().toISOString();
  let kind = classifyClipboardText(text);
  const draft = parseAgentTrace(text, 'clipboard-capture.json', capturedAt);
  if (draft.source_profile?.detected_trace_format === 'standalone_source_file' && kind !== 'operator_thread_export') {
    kind = 'code_file';
  }
  const sourceBytes = countValue(payload.text_bytes || payload.source_bytes || payload.bytes) || byteLength(text);
  const contentBytes = countValue(payload.content_bytes || payload.clipboard_bytes) || sourceBytes;
  const filename = `clip-${filenameStamp(capturedAt)}-${kind}-${draft.source.input_hash}.json`;
  draft.source.name = filename;
  draft.source.input_bytes = sourceBytes;
  draft.capture_context = {
    captured_from: 'macos_clipboard_watcher',
    capture_kind: kind,
    clipboard_change_count: payload.change_count ?? null,
    captured_at: capturedAt,
    autosaved: true,
    input_bytes: sourceBytes,
    source_bytes: sourceBytes,
    content_bytes: contentBytes,
    clipboard_bytes: contentBytes,
    bytes_source: payload.bytes_source || 'utf8_text',
    content_kind: payload.content_kind || 'text',
    file_count: countValue(payload.file_count),
  };
  return { packet: draft, filename, kind, capturedAt };
}

function captureTimeLabel(value) {
  const date = value ? new Date(value) : new Date();
  return Number.isNaN(date.getTime()) ? 'recent' : date.toLocaleTimeString();
}

function countValue(value) {
  const number = Number(value || 0);
  return Number.isFinite(number) ? number : 0;
}

function normalizeClipboardSnapshot(payload = {}) {
  const contentBytes = countValue(payload.contentBytes || payload.content_bytes || payload.clipboardBytes || payload.clipboard_bytes || payload.bytes);
  const textBytes = countValue(payload.textBytes || payload.text_bytes);
  const fileBytes = countValue(payload.fileBytes || payload.file_bytes);
  const itemBytes = countValue(payload.itemBytes || payload.item_bytes);
  const fileCount = countValue(payload.fileCount || payload.file_count);
  const capturedAt = payload.capturedAt || payload.captured_at || new Date().toISOString();
  const contentKind = payload.contentKind || payload.content_kind || (fileCount ? 'file' : textBytes ? 'text' : 'pasteboard_item');
  if (!contentBytes && !textBytes && !fileBytes && !itemBytes) return null;
  return {
    capturedAt,
    changeCount: payload.changeCount ?? payload.change_count ?? null,
    contentKind,
    bytesSource: payload.bytesSource || payload.bytes_source || '',
    contentBytes: contentBytes || fileBytes || textBytes || itemBytes,
    textBytes,
    fileBytes,
    fileCount,
    itemBytes,
    pasteboardTypes: Array.isArray(payload.pasteboardTypes)
      ? payload.pasteboardTypes
      : Array.isArray(payload.pasteboard_types) ? payload.pasteboard_types : [],
  };
}

function rememberClipboardSnapshot(payload = {}, options = {}) {
  const snapshot = normalizeClipboardSnapshot(payload);
  if (!snapshot) return null;
  latestClipboardSnapshot = snapshot;
  if (options.flash === false) {
    renderTopSummary();
  } else {
    markClipboardSignal();
  }
  return snapshot;
}

function clipboardKindLabel(snapshot) {
  if (!snapshot) return 'Clipboard';
  if (snapshot.contentKind === 'files') return `${fmt(snapshot.fileCount)} files`;
  if (snapshot.contentKind === 'file') return snapshot.fileCount > 1 ? `${fmt(snapshot.fileCount)} files` : 'File';
  if (snapshot.contentKind === 'pasteboard_item') return 'Clipboard item';
  return formatKind(snapshot.contentKind);
}

function bytesDiffer(left, right) {
  const a = countValue(left);
  const b = countValue(right);
  return a > 0 && b > 0 && Math.abs(a - b) >= Math.max(1024, Math.min(a, b) * 0.05);
}

function captureByteSummary(sourceBytes, contentBytes, artifactBytes) {
  const source = countValue(sourceBytes);
  const content = countValue(contentBytes) || source;
  const artifact = countValue(artifactBytes);
  const label = content ? `clip ${formatBytes(content)}` : formatBytes(source);
  return artifact && bytesDiffer(content || source, artifact)
    ? `${label} · json ${formatBytes(artifact)}`
    : label;
}

function captureSummaryText(capture) {
  const sourceBytes = capture.bytes || capture.sourceBytes || capture.chars;
  const trailing = `${captureByteSummary(sourceBytes, capture.contentBytes, capture.artifactBytes)} · ${ageLabel(capture.capturedAt)}`;
  if (capture.missionTitle) {
    const provider = capture.missionProvider || 'agent';
    const turn = capture.missionTurnIndex ? ` · turn ${capture.missionTurnIndex}` : '';
    const tools = capture.missionToolCount ? ` · ${capture.missionToolCount} tools` : '';
    const errs = capture.missionErrorCount ? ` · ${capture.missionErrorCount} err` : '';
    const title = capture.missionTitle.length > 60 ? `${capture.missionTitle.slice(0, 57).trim()}…` : capture.missionTitle;
    return `TRACE ${provider} · ${title}${turn}${tools}${errs} · ${trailing}`;
  }
  // cli_prompt_trace clips survive Swift normalization through hud_caption.
  // Pattern "<provider> · <title> · turn N · M tools" is the python feeder format.
  if (capture.hudCaption && /·\s*turn\s+\d+\s+·\s+\d+\s+tools?\b/i.test(capture.hudCaption)) {
    return `TRACE ${capture.hudCaption} · ${trailing}`;
  }
  return `${formatKind(capture.kind)} · ${trailing}`;
}

function clipboardSnapshotSummaryText(snapshot) {
  return `${clipboardKindLabel(snapshot)} · ${formatBytes(snapshot.contentBytes)} · ${ageLabel(snapshot.capturedAt)}`;
}

function latestSummarySurface() {
  const capture = latestCapture();
  if (!latestClipboardSnapshot) return capture ? { type: 'capture', value: capture } : null;
  if (!capture) return { type: 'snapshot', value: latestClipboardSnapshot };
  const snapshotMs = new Date(latestClipboardSnapshot.capturedAt).getTime();
  const captureMs = new Date(capture.capturedAt).getTime();
  if (Number.isFinite(snapshotMs) && (!Number.isFinite(captureMs) || snapshotMs > captureMs + 2000)) {
    return { type: 'snapshot', value: latestClipboardSnapshot };
  }
  return { type: 'capture', value: capture };
}

function normalizeCapture(row = {}) {
  const capturedAt = row.capturedAt || row.captured_at || row.recorded_at || new Date().toISOString();
  const inputHash = row.inputHash || row.input_hash || '';
  const path = row.path || row.exportPath || row.export_path || row.downloadPath || row.download_path || row.displayPath || row.display_path || '';
  const storedPath = row.storedPath || row.stored_path || '';
  const fullPacketPath = row.fullPacketPath || row.full_packet_path || storedPath;
  const rawPath = row.rawPath || row.raw_path || '';
  const clipStorePath = row.clipStorePath || row.clip_store_path || '';
  const exportPath = row.exportPath || row.export_path || path;
  const filename =
    row.filename ||
    (path ? path.split('/').pop() : '') ||
    (clipStorePath ? clipStorePath.split('/').pop() : '') ||
    (storedPath ? storedPath.split('/').pop() : '') ||
    'clipboard-capture.json';
  const kind = normalizedKind(row.kind);
  const chars = countValue(row.chars);
  const bytes = countValue(row.bytes || row.sourceBytes || row.source_bytes) || chars;
  const contentBytes = countValue(row.contentBytes || row.content_bytes || row.clipboardBytes || row.clipboard_bytes) || bytes;
  const artifactBytes = countValue(row.artifactBytes || row.artifact_bytes);
  const fullPacketBytes = countValue(row.fullPacketBytes || row.full_packet_bytes);
  const clipBytes = countValue(row.clipBytes || row.clip_bytes);
  const rawBytes = countValue(row.rawBytes || row.raw_bytes);
  const events = countValue(row.events);
  const ids = countValue(row.ids);
  const artifacts = countValue(row.artifacts);
  const sourceLines = countValue(row.sourceLines || row.source_lines || row.sourceLineCount || row.source_line_count);
  const sourceChunks = countValue(row.sourceChunks || row.source_chunks || row.sourceChunkCount || row.source_chunk_count);
  const patterns = countValue(row.patterns);
  const cliPromptTrace = row.cliPromptTrace || row.cli_prompt_trace || null;
  const missionTitle = cliPromptTrace
    ? (cliPromptTrace.title || '')
    : '';
  const missionTitleSource = cliPromptTrace
    ? (cliPromptTrace.title_source || cliPromptTrace.titleSource || '')
    : '';
  const missionProvider = cliPromptTrace
    ? (cliPromptTrace.provider || row.provider || '')
    : (row.provider || '');
  const missionSessionId = cliPromptTrace
    ? (cliPromptTrace.session_id || cliPromptTrace.sessionId || '')
    : '';
  const missionTurnIndex = cliPromptTrace
    ? countValue(cliPromptTrace.turn_index ?? cliPromptTrace.turnIndex)
    : 0;
  const missionToolCount = cliPromptTrace
    ? countValue(cliPromptTrace.tool_count ?? cliPromptTrace.toolCount)
    : 0;
  const missionErrorCount = cliPromptTrace
    ? countValue(cliPromptTrace.error_count ?? cliPromptTrace.errorCount)
    : 0;
  const hudCaption = row.hudCaption || row.hud_caption || `${formatKind(kind)} · ${captureByteSummary(bytes, contentBytes, artifactBytes)} · ${fmt(events)} events`;
  return {
    filename,
    path,
    storedPath,
    fullPacketPath,
    rawPath,
    clipStorePath,
    exportPath,
    missionTitle,
    missionTitleSource,
    missionProvider,
    missionSessionId,
    missionTurnIndex,
    missionToolCount,
    missionErrorCount,
    storageScope: row.storageScope || row.storage_scope || (path ? 'downloads_export' : storedPath ? 'private_capture_store' : 'memory'),
    kind,
    chars,
    bytes,
    sourceBytes: bytes,
    contentBytes,
    artifactBytes,
    fullPacketBytes,
    clipBytes,
    rawBytes,
    bytesSource: row.bytesSource || row.bytes_source || '',
    contentKind: row.contentKind || row.content_kind || '',
    fileCount: countValue(row.fileCount || row.file_count),
    events,
    artifacts,
    ids,
    commands: countValue(row.commands),
    mutations: countValue(row.mutations),
    validations: countValue(row.validations),
    sourceLines,
    sourceChunks,
    patterns,
    inputHash,
    capturedAt,
    timeLabel: row.timeLabel || row.time_label || captureTimeLabel(capturedAt),
    hudCaption,
  };
}

function captureKey(capture) {
  if (capture.inputHash) return `hash:${capture.inputHash}`;
  return capture.storedPath || capture.path || capture.filename;
}

function sleep(ms) {
  return new Promise((resolve) => {
    window.setTimeout(resolve, ms);
  });
}

function yieldToRenderer(timeoutMs = 50) {
  return new Promise((resolve) => {
    let settled = false;
    const finish = () => {
      if (settled) return;
      settled = true;
      resolve();
    };
    window.setTimeout(finish, timeoutMs);
    if (typeof window.requestAnimationFrame === 'function') {
      window.requestAnimationFrame(() => window.setTimeout(finish, 0));
    } else {
      window.setTimeout(finish, 0);
    }
  });
}

function waitForClipboardCaptureAfter(serial, timeoutMs = 900) {
  const start = Date.now();
  return new Promise((resolve) => {
    const check = () => {
      if (clipboardCaptureSerial > serial || Date.now() - start >= timeoutMs) {
        resolve();
        return;
      }
      window.setTimeout(check, 50);
    };
    check();
  });
}

function rememberCapture(capture, limit = CAPTURE_HISTORY_MEMORY_LIMIT) {
  const normalized = normalizeCapture(capture);
  const key = captureKey(normalized);
  savedCaptures = savedCaptures.filter((item) => captureKey(item) !== key);
  savedCaptures.unshift(normalized);
  if (savedCaptures.length > limit) savedCaptures.length = limit;
  renderSavedCaptures();
  return normalized;
}

function hydrateCaptureHistory(rows) {
  if (!Array.isArray(rows)) return;
  savedCaptures = rows.map(normalizeCapture).filter((row) => captureKey(row)).slice(0, CAPTURE_HISTORY_MEMORY_LIMIT);
  renderSavedCaptures();
}

function recordCapture(capture) {
  postNative('recordCapture', {
    capture: {
      filename: capture.filename,
      path: capture.path,
      stored_path: capture.storedPath,
      full_packet_path: capture.fullPacketPath,
      raw_path: capture.rawPath,
      clip_store_path: capture.clipStorePath,
      export_path: capture.exportPath,
      storage_scope: capture.storageScope,
      kind: capture.kind,
      input_hash: capture.inputHash,
      captured_at: capture.capturedAt,
      time_label: capture.timeLabel,
      hud_caption: capture.hudCaption,
      chars: capture.chars,
      bytes: capture.bytes,
      source_bytes: capture.sourceBytes,
      clipboard_bytes: capture.contentBytes,
      content_bytes: capture.contentBytes,
      artifact_bytes: capture.artifactBytes,
      full_packet_bytes: capture.fullPacketBytes,
      clip_bytes: capture.clipBytes,
      raw_bytes: capture.rawBytes,
      content_kind: capture.contentKind,
      bytes_source: capture.bytesSource,
      file_count: capture.fileCount,
      events: capture.events,
      artifacts: capture.artifacts,
      ids: capture.ids,
      commands: capture.commands,
      mutations: capture.mutations,
      validations: capture.validations,
      source_lines: capture.sourceLines,
      source_chunks: capture.sourceChunks,
      patterns: capture.patterns,
    },
  });
}

function findExistingCapture(packet) {
  const inputHash = packet?.source?.input_hash || '';
  if (!inputHash) return null;
  return savedCaptures.find((capture) => capture.inputHash === inputHash && (capture.storedPath || capture.clipStorePath || capture.path)) || null;
}

function latestCapture() {
  return savedCaptures.find((capture) => capture.storedPath || capture.clipStorePath || capture.path) || savedCaptures[0] || null;
}

function renderTopSummary() {
  const latest = latestCapture();
  const surface = latestSummarySurface();
  const signal = signalPresentation(surface?.value || null);
  if (els.latestSummary) {
    els.latestSummary.textContent = surface
      ? surface.type === 'snapshot'
        ? clipboardSnapshotSummaryText(surface.value)
        : captureSummaryText(surface.value)
      : 'watching clipboard';
    els.latestSummary.title = surface?.type === 'snapshot'
      ? `${surface.value.bytesSource || 'clipboard'} · ${surface.value.pasteboardTypes.join(', ')}`
      : latest?.path || latest?.filename || '';
  }
  if (els.clipboardSignal) {
    els.clipboardSignal.className = `signal-dot ${signal.state}`;
    els.clipboardSignal.style.setProperty('--signal-color', signal.color);
    els.clipboardSignal.style.setProperty('--signal-rgb', signal.rgb.join(', '));
  }
  document.body.dataset.clipboardSignal = signal.state;
  document.body.style.setProperty('--signal-color', signal.color);
  document.body.style.setProperty('--signal-rgb', signal.rgb.join(', '));
  if (els.buttons.latest) {
    const canNativeReveal = hasNativeBridge('revealLatestCapture');
    const canRevealWithoutNative = Boolean(latest?.path);
    els.buttons.latest.disabled = latestRevealPending || (!canNativeReveal && !canRevealWithoutNative);
  }
}

function setLatestRevealPending(pending) {
  latestRevealPending = Boolean(pending);
  if (!latestRevealPending && latestRevealTimeout) {
    window.clearTimeout(latestRevealTimeout);
    latestRevealTimeout = 0;
  }
  if (els.buttons.latest) {
    els.buttons.latest.textContent = latestRevealPending ? 'Finding...' : 'Find latest';
    els.buttons.latest.setAttribute('aria-busy', latestRevealPending ? 'true' : 'false');
  }
  renderTopSummary();
}

function statValue(value) {
  if (typeof value === 'number') return fmt(value);
  return escapeHtml(value);
}

function renderStats(packet, clipPayload = null) {
  const items = [
    ['events', packet.summary.events],
    ['commands', packet.summary.commands],
    ['mutations', packet.summary.mutations],
    ['validations', packet.summary.validations],
    ['artifacts', packet.summary.artifacts || 0],
    ['chunks', packet.summary.source_chunks || 0],
    ['clip', clipPayload ? formatBytes(clipPayload.bytes) : '0 bytes'],
    ['raw', formatBytes(packet.source?.input_bytes || 0)],
    ['paths', packet.summary.paths],
    ['ids', packet.summary.ids],
    ['sections', packet.summary.sections],
  ];
  els.stats.innerHTML = items
    .map(([label, value]) => `<div class="stat"><span>${label}</span><strong>${statValue(value)}</strong></div>`)
    .join('');
}

function renderContract(packet, clipPayload = null) {
  const clip = clipPayload?.packet;
  const contract = clip?.clip_contract;
  const order = contract?.parse_order?.slice(0, 10).join(' -> ')
    || packet.ai_parse_contract.read_order.slice(0, 9).join(' -> ');
  const label = contract ? `${clip.carrier_mode} · ${contract.source_authority_field}` : 'AI parse order';
  els.contract.innerHTML = `<span>Clip JSON</span><code>${escapeHtml(label)} · ${escapeHtml(order)}</code>`;
}

function clipIndexSummary(clip) {
  if (!clip) return 'waiting';
  const indexes = [
    clip.reader_index ? 'reader' : null,
    clip.command_ledger ? `${fmt(clip.command_ledger.command_count)} cmds` : null,
    clip.terminal_state_index ? 'terminal' : null,
    clip.validation_matrix ? `${fmt(clip.validation_matrix.validation_count)} proofs` : null,
    clip.artifact_delta_index ? `${fmt(clip.artifact_delta_index.rows?.length || 0)} artifacts` : null,
    clip.long_line_index?.long_line_count ? `${fmt(clip.long_line_index.long_line_count)} long lines` : null,
  ].filter(Boolean);
  return indexes.length ? indexes.join(' · ') : 'no indexes';
}

function renderCaptureProfile(packet, clipPayload = null, detectedKind = 'text') {
  const kind = packet.capture_context?.capture_kind || detectedKind;
  const traceFormat = packet.source_profile?.detected_trace_format || 'unknown';
  if (els.captureProfile) {
    els.captureProfile.textContent = `Capture: ${formatKind(kind)} · ${traceFormat} · ${formatBytes(packet.source?.input_bytes || 0)}`;
    els.captureProfile.classList.toggle('prompt', kind === 'prompt');
  }
  if (els.clipProfile) {
    const clip = clipPayload?.packet;
    els.clipProfile.textContent = clip
      ? `Clip: ${clip.carrier_mode} · ${clipIndexSummary(clip)} · ${formatBytes(clipPayload.bundleBytes)}`
      : 'Clip: waiting';
  }
}

function renderJson(packet, clipPayload = null) {
  const clip = clipPayload?.packet || attachmentClipPayload(packet).packet;
  els.json.textContent = JSON.stringify(previewClipPacket(clip), null, 2);
}

function renderTimeline(packet, query) {
  const events = packet.timeline
    .filter((event) => {
      if (!query) return true;
      return matches(`${event.kind} ${event.title} ${event.snippet} ${event.entities.paths.join(' ')} ${event.entities.ids.join(' ')}`, query);
    })
    .slice(0, 220);

  els.timeline.innerHTML = events.length
    ? events
        .map(
          (event) => `
            <article class="row">
              <div class="row-head">
                <span class="badge ${eventClass(event.kind, event.status)}">${escapeHtml(event.kind)}</span>
                <span class="muted">${lineRange(event.line_range)}</span>
                ${event.status !== 'not_stated' ? `<span class="badge ${eventClass(event.kind, event.status)}">${event.status}</span>` : ''}
              </div>
              <div class="row-title">${escapeHtml(event.title)}</div>
              <pre>${escapeHtml(event.snippet)}</pre>
            </article>
          `,
        )
        .join('')
    : '<div class="empty">No matching events.</div>';
}

function renderEntityTabs(packet) {
  const groups = [
    ['paths', 'Paths'],
    ['commands', 'Commands'],
    ['ids', 'Ids'],
    ['hashes', 'Hashes'],
  ];
  els.entityTabs.innerHTML = groups
    .map(([id, label]) => {
      const active = id === activeEntityGroup ? 'active' : '';
      return `<button class="tab ${active}" data-entity-group="${id}">${label} <span>${fmt(packet.entities[id].length)}</span></button>`;
    })
    .join('');
}

function renderEntities(packet, query) {
  const rows = packet.entities[activeEntityGroup]
    .filter((row) => !query || matches(`${row.kind} ${row.value}`, query))
    .slice(0, 120);

  els.entities.innerHTML = rows.length
    ? rows
        .map(
          (row) => `
            <article class="entity">
              <code>${escapeHtml(row.value)}</code>
              <span>${fmt(row.count)}</span>
              <small>L${row.first_line}${row.last_line !== row.first_line ? `-L${row.last_line}` : ''}</small>
            </article>
          `,
        )
        .join('')
    : '<div class="empty">No matching entities.</div>';
}

function renderSections(packet, query) {
  const rows = packet.sections
    .filter((section) => !query || matches(`${section.title} ${section.preview}`, query))
    .slice(0, 80);

  els.sections.innerHTML = rows.length
    ? rows
        .map(
          (section) => `
            <article class="row">
              <div class="row-head">
                <span class="badge">section</span>
                <span class="muted">${lineRange(section.line_range)}</span>
              </div>
              <div class="row-title">${escapeHtml(section.title)}</div>
              <pre>${escapeHtml(section.preview)}</pre>
            </article>
          `,
        )
        .join('')
    : '<div class="empty">No detected sections.</div>';
}

function renderSavedCaptures() {
  if (els.buttons.clearHistory) els.buttons.clearHistory.disabled = savedCaptures.length === 0;
  renderTopSummary();
  els.savedList.innerHTML = savedCaptures.length
    ? savedCaptures
        .slice(0, CAPTURE_HISTORY_DISPLAY_LIMIT)
        .map(
          (capture) => `
            <article class="saved-item">
              <code title="${escapeHtml(capture.path || capture.storedPath || capture.filename)}">${escapeHtml(capture.filename)}</code>
              <div class="saved-actions">
                <button type="button" data-export-capture="${escapeHtml(captureKey(capture))}" data-stored-path="${escapeHtml(capture.storedPath || capture.fullPacketPath)}" data-export-path="${escapeHtml(capture.path)}" data-input-hash="${escapeHtml(capture.inputHash)}" ${capture.storedPath || capture.clipStorePath || capture.path ? '' : 'disabled'}>${capture.path ? 'Reveal' : 'Export'}</button>
                <button type="button" data-copy-path="${escapeHtml(capture.path)}" ${capture.path ? '' : 'disabled'}>Path</button>
              </div>
              <div class="saved-meta">${escapeHtml(formatKind(capture.kind))} · ${capture.path ? 'clip exported' : 'private triplet'} · ${escapeHtml(captureByteSummary(capture.bytes || capture.chars, capture.contentBytes, capture.clipBytes || capture.artifactBytes))}${capture.fullPacketBytes ? ` · full ${escapeHtml(formatBytes(capture.fullPacketBytes))}` : ''}${capture.rawBytes ? ` · raw ${escapeHtml(formatBytes(capture.rawBytes))}` : ''} · ${fmt(capture.events)} events${capture.artifacts ? ` · ${fmt(capture.artifacts)} artifacts` : ''}${capture.sourceChunks ? ` · ${fmt(capture.sourceChunks)} chunks` : ''}${capture.sourceLines ? ` · ${fmt(capture.sourceLines)} lines` : ''} · ${fmt(capture.ids)} ids · ${ageLabel(capture.capturedAt)}${capture.inputHash ? ` · ${escapeHtml(capture.inputHash)}` : ''}</div>
            </article>
          `,
        )
        .join('')
    : '<div class="empty">No clipboard captures yet.</div>';
}

function addSavedCapture(result, packet, kind, capturedAt, options = {}) {
  const filename = result.filename || packet.source.name;
  const path = result.path || '';
  const context = packet.capture_context || {};
  const sourceBytes = packet.source.input_bytes || byteLength(els.source.value);
  const contentBytes = countValue(context.content_bytes || context.clipboard_bytes) || sourceBytes;
  const artifactBytes = countValue(result.artifact_bytes || result.artifactBytes || options.artifactBytes);
  const existing = packet?.source?.input_hash
    ? savedCaptures.find((capture) => capture.inputHash === packet.source.input_hash)
    : null;
  const capture = rememberCapture({
    filename,
    path,
    storedPath: result.stored_path || result.storedPath || existing?.storedPath || '',
    fullPacketPath: result.full_packet_path || result.fullPacketPath || result.stored_path || result.storedPath || existing?.fullPacketPath || existing?.storedPath || '',
    rawPath: result.raw_path || result.rawPath || existing?.rawPath || '',
    clipStorePath: result.clip_store_path || result.clipStorePath || existing?.clipStorePath || '',
    exportPath: result.export_path || result.exportPath || path,
    storageScope: result.storage_scope || result.storageScope || (path ? 'downloads_export' : 'memory'),
    kind,
    chars: packet.source.input_chars,
    bytes: sourceBytes,
    sourceBytes,
    contentBytes,
    artifactBytes,
    fullPacketBytes: countValue(result.full_packet_bytes || result.fullPacketBytes || existing?.fullPacketBytes),
    clipBytes: countValue(result.clip_bytes || result.clipBytes || artifactBytes || existing?.clipBytes),
    rawBytes: countValue(result.raw_bytes || result.rawBytes || existing?.rawBytes),
    bytesSource: context.bytes_source || '',
    contentKind: context.content_kind || '',
    fileCount: countValue(context.file_count),
    events: packet.summary.events,
    artifacts: packet.summary.artifacts || 0,
    ids: packet.summary.ids,
    commands: packet.summary.commands,
    mutations: packet.summary.mutations,
    validations: packet.summary.validations,
    sourceLines: packet.source.input_lines,
    sourceChunks: packet.summary.source_chunks || 0,
    patterns: packet.summary.patterns || 0,
    inputHash: packet.source.input_hash,
    capturedAt: capturedAt || packet.generated_at,
    timeLabel: captureTimeLabel(capturedAt || packet.generated_at),
    hudCaption: `${formatKind(kind)} · ${captureByteSummary(sourceBytes, contentBytes, artifactBytes)} · ${fmt(packet.summary.events)} events`,
  });
  if (options.persist !== false) recordCapture(capture);
  return capture;
}

function captureMetadata(filename, packet, kind, capturedAt, artifactBytes = 0, sizes = {}) {
  const context = packet.capture_context || {};
  const sourceBytes = packet.source.input_bytes || byteLength(els.source.value);
  const contentBytes = countValue(context.content_bytes || context.clipboard_bytes) || sourceBytes;
  const clipBytes = countValue(sizes.clipBytes || sizes.clip_bytes) || artifactBytes;
  const fullPacketBytes = countValue(sizes.fullPacketBytes || sizes.full_packet_bytes);
  const rawBytes = countValue(sizes.rawBytes || sizes.raw_bytes) || sourceBytes;
  return {
    filename,
    kind,
    input_hash: packet.source.input_hash,
    captured_at: capturedAt || packet.generated_at,
    time_label: captureTimeLabel(capturedAt || packet.generated_at),
    hud_caption: `${formatKind(kind)} · ${captureByteSummary(sourceBytes, contentBytes, artifactBytes)} · ${fmt(packet.summary.events)} events`,
    chars: packet.source.input_chars,
    bytes: sourceBytes,
    source_bytes: sourceBytes,
    clipboard_bytes: contentBytes,
    content_bytes: contentBytes,
    artifact_bytes: artifactBytes,
    full_packet_bytes: fullPacketBytes,
    clip_bytes: clipBytes,
    raw_bytes: rawBytes,
    content_kind: context.content_kind || '',
    bytes_source: context.bytes_source || '',
    file_count: countValue(context.file_count),
    events: packet.summary.events,
    artifacts: packet.summary.artifacts || 0,
    ids: packet.summary.ids,
    commands: packet.summary.commands,
    mutations: packet.summary.mutations,
    validations: packet.summary.validations,
    source_lines: packet.source.input_lines,
    source_chunks: packet.summary.source_chunks || 0,
    patterns: packet.summary.patterns || 0,
  };
}

async function storeCapture(filename, packet, kind, capturedAt) {
  const safeName = ensureJsonFilename(filename);
  const fullJsonText = JSON.stringify(packet, null, 2);
  const fullPacketBytes = byteLength(fullJsonText);
  const clipPayload = attachmentClipPayload(packet);
  const artifactBytes = clipPayload.bytes;
  const metadata = captureMetadata(safeName, packet, kind, capturedAt, artifactBytes, {
    fullPacketBytes,
    clipBytes: clipPayload.bytes,
    rawBytes: packet.lossless_source?.source_text_bytes || packet.source?.input_bytes || 0,
  });

  if (hasNativeBridge('storeCaptureJson')) {
    if (fullPacketBytes > NATIVE_STORE_PAYLOAD_LIMIT_BYTES) {
      const capture = rememberCapture({
        ...metadata,
        filename: safeName,
        storage_scope: 'memory_oversize_native_store_skipped',
        skip_reason: 'full_packet_too_large_for_native_bridge',
      });
      return {
        ok: true,
        filename: safeName,
        path: '',
        storage_scope: 'memory_oversize_native_store_skipped',
        skipped_private_store: true,
        reason: 'full_packet_too_large_for_native_bridge',
        full_packet_bytes: fullPacketBytes,
        native_store_limit_bytes: NATIVE_STORE_PAYLOAD_LIMIT_BYTES,
        capture,
      };
    }
    const result = await nativeStoreCapture(safeName, fullJsonText, metadata, clipPayload.jsonText, []);
    const capture = rememberCapture(result.capture || { ...metadata, ...result });
    return { ...result, capture };
  }

  const capture = rememberCapture({ ...metadata, storageScope: 'memory' });
  return { ok: true, filename: safeName, path: '', storage_scope: 'memory', capture };
}

function render() {
  const text = els.source.value;
  const filename = ensureJsonFilename(els.filename.value);
  currentPacket = parseAgentTrace(text, filename, currentGeneratedAt || new Date().toISOString());
  currentPacket.source.input_bytes = byteLength(text);
  const query = els.query.value.trim();
  const detectedKind = currentPacket.capture_context?.capture_kind || classifyClipboardText(text);
  const clipPayload = attachmentClipPayload(currentPacket);

  renderContract(currentPacket, clipPayload);
  renderStats(currentPacket, clipPayload);
  renderJson(currentPacket, clipPayload);
  renderCaptureProfile(currentPacket, clipPayload, detectedKind);
  renderTimeline(currentPacket, query);
  renderEntityTabs(currentPacket);
  renderEntities(currentPacket, query);
  renderSections(currentPacket, query);

  const hasSource = text.trim().length > 0;
  if (els.buttons.copy) els.buttons.copy.disabled = !hasSource;
  if (els.buttons.download) els.buttons.download.disabled = !hasSource;
  if (els.buttons.clear) els.buttons.clear.disabled = !hasSource;
  renderTopSummary();
}

function renderWatchState() {
  const native = hasNativeBridge('clipboardControl');
  els.watchState.classList.toggle('live', native && clipboardWatchEnabled);
  els.watchState.classList.toggle('paused', native && !clipboardWatchEnabled);
  els.watchState.textContent = native
    ? clipboardWatchEnabled
      ? 'Watching'
      : 'Paused'
    : 'Watcher unavailable';
  if (els.buttons.toggleWatch) {
    els.buttons.toggleWatch.disabled = !native;
    els.buttons.toggleWatch.textContent = clipboardWatchEnabled ? 'Pause Watch' : 'Resume Watch';
  }
}

function renderSaveTarget() {
  if (hasNativeBridge('storeCaptureJson')) {
    els.saveTarget.textContent = 'Auto-store: raw/full + latest 10 clip exports';
  } else if (window.location.protocol.startsWith('http')) {
    els.saveTarget.textContent = 'Manual download only';
  } else {
    els.saveTarget.textContent = 'Manual download only';
  }
  renderWatchState();
}

function loadSource(text, filename, status, generatedAt = null) {
  currentGeneratedAt = generatedAt;
  els.source.value = text;
  els.filename.value = filename;
  render();
  els.status.textContent = status;
}

async function handleClipboardText(payload) {
  clipboardCaptureSerial += 1;
  const captureWork = (async () => {
    rememberClipboardSnapshot(payload, { flash: true });
    const text = payload.text || '';
    if (!text.trim()) {
      els.status.textContent = 'Clipboard updated.';
      return;
    }
    els.status.textContent = 'Clipboard detected; structuring capture.';
    await yieldToRenderer();

    const { packet, filename, kind, capturedAt } = buildClipboardPacket(text, payload);
    currentGeneratedAt = capturedAt;
    els.source.value = text;
    els.filename.value = filename;
    currentPacket = packet;
    markClipboardSignal();
    await yieldToRenderer(25);

    try {
      const result = await storeCapture(filename, packet, kind, capturedAt);
      els.status.textContent = result.skipped_private_store
        ? `Clipboard loaded; large packet kept in this window (${_formatKB(result.full_packet_bytes)}).`
        : result.capture?.path
        ? `Captured and exported: ${result.capture.filename || result.filename || filename}.`
        : `Captured privately: ${result.filename || filename}.`;
      markClipboardSignal();
    } catch (error) {
      els.status.textContent = `Clipboard loaded; private capture failed: ${error.message}`;
    } finally {
      render();
    }
  })();
  latestCapturePromise = captureWork.catch(() => {});
  return captureWork;
}

async function pasteFromClipboard() {
  if (postNative('readClipboardNow')) {
    els.status.textContent = 'Reading clipboard through native watcher.';
    return;
  }

  try {
    const text = await navigator.clipboard.readText();
    if (!text) {
      els.status.textContent = 'Clipboard was empty.';
      return;
    }
    loadSource(text, ensureJsonFilename(els.filename.value), `Loaded ${fmt(text.length)} chars from clipboard.`);
  } catch {
    els.status.textContent = 'Clipboard read blocked. The native app watcher avoids this permission path.';
    els.source.focus();
  }
}

async function copyJson() {
  try {
    const payload = attachmentClipPayload(currentPacket);
    await navigator.clipboard.writeText(payload.jsonText);
    els.status.textContent = payload.sidecars.length
      ? 'Compressed clip copied (thin attachment clip — near raw size). Sidecar required for exact restore.'
      : 'Compressed clip copied (thin attachment clip — near raw size, much smaller than the full parsed packet).';
  } catch {
    els.status.textContent = 'Copy blocked.';
  }
}

async function copyText(value) {
  try {
    await navigator.clipboard.writeText(value);
    els.status.textContent = 'Path copied.';
  } catch {
    els.status.textContent = 'Copy path blocked.';
  }
}

async function importFile(file) {
  if (!file) return;
  const text = await file.text();
  loadSource(text, file.name.replace(/\.(txt|log|md)$/i, '.json'), `Loaded ${file.name}.`);
}

async function revealLatestFile() {
  if (latestRevealPending) return;
  if (hasNativeBridge('revealLatestCapture')) {
    setLatestRevealPending(true);
    els.status.textContent = 'Finding latest saved capture.';
    const beforeSerial = clipboardCaptureSerial;
    const readRequested = postNative('readClipboardNow');
    if (readRequested) {
      await waitForClipboardCaptureAfter(beforeSerial);
      await sleep(80);
      await latestCapturePromise;
    }
    postNative('requestCaptureHistory');
    if (postNative('revealLatestCapture')) {
      latestRevealTimeout = window.setTimeout(() => {
        if (!latestRevealPending) return;
        setLatestRevealPending(false);
        els.status.textContent = 'Find latest did not get a native response.';
      }, 12000);
      return;
    }
    setLatestRevealPending(false);
  }
  const latest = latestCapture();
  if (latest?.path && postNative('revealFile', { path: latest.path })) {
    els.status.textContent = 'Opening the most recent capture in Finder.';
    return;
  }
  els.status.textContent = 'No saved capture file yet.';
}

function reinstallMismatchCount() {
  const freshness = resourceFreshnessPayload();
  return Number(freshness.blocking_mismatch_count ?? freshness.mismatch_count ?? 0) || 0;
}

function clearReinstallReceiptTimeout() {
  if (!reinstallReceiptTimeout) return;
  window.clearTimeout(reinstallReceiptTimeout);
  reinstallReceiptTimeout = 0;
}

function clearReinstallRelaunchTimeout() {
  if (!reinstallRelaunchTimeout) return;
  window.clearTimeout(reinstallRelaunchTimeout);
  reinstallRelaunchTimeout = 0;
}

function armReinstallRelaunchWatchdog(installed = false) {
  clearReinstallRelaunchTimeout();
  const requestId = reinstallRequestId;
  reinstallRelaunchTimeout = window.setTimeout(() => {
    if (!reinstallInFlight) return;
    if (requestId && reinstallRequestId && reinstallRequestId !== requestId) return;
    reinstallRequestId = '';
    setReinstallPending(false, 'failed');
    els.status.textContent = installed
      ? 'Reinstall finished, but this window did not relaunch. Retry reinstall or reopen /Applications/Agent Trace Structurer.app.'
      : 'Reinstall started, but this window did not close. Retry reinstall or reopen /Applications/Agent Trace Structurer.app.';
  }, REINSTALL_RELAUNCH_TIMEOUT_MS);
}

function syncReinstallButtonState(state = 'ready') {
  const button = els.buttons.reinstallApp;
  if (!button) return;
  const stale = isResourceBundleStale();
  const mismatchCount = reinstallMismatchCount();
  button.dataset.freshness = resourceFreshnessPayload().status || 'unknown';
  button.dataset.reinstallState = state;
  if (reinstallInFlight) return;
  button.disabled = false;
  button.setAttribute('aria-busy', 'false');
  button.textContent = state === 'failed'
    ? 'Retry reinstall'
    : stale
      ? 'Reinstall stale'
      : 'Reinstall app';
  button.title = stale
    ? `Rebuild, reinstall, and relaunch from current repo source (${mismatchCount || 1} blocking resource mismatch${(mismatchCount || 1) === 1 ? '' : 'es'}).`
    : 'Rebuild, reinstall, and relaunch the native app from the current repo source.';
}

function setReinstallPending(pending, stage = 'starting') {
  reinstallInFlight = pending;
  const button = els.buttons.reinstallApp;
  if (!button) return;
  button.disabled = pending;
  button.setAttribute('aria-busy', pending ? 'true' : 'false');
  button.dataset.reinstallState = pending ? stage : 'ready';
  if (pending) {
    button.textContent = stage === 'relaunching' ? 'Relaunching' : 'Starting reinstall';
    button.title = 'Reinstall requested. The app will close, replace the installed bundle, and relaunch.';
    return;
  }
  syncReinstallButtonState(stage === 'failed' ? 'failed' : 'ready');
}

function reinstallAppBundle() {
  if (reinstallInFlight) return;
  const requestId = `reinstall-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
  reinstallRequestId = requestId;
  clearReinstallRelaunchTimeout();
  setReinstallPending(true, 'starting');
  const stale = isResourceBundleStale();
  const mismatchCount = reinstallMismatchCount();
  els.status.textContent = stale
    ? `Reinstalling stale app bundle (${mismatchCount || 1} blocking mismatch${(mismatchCount || 1) === 1 ? '' : 'es'}); the window will relaunch.`
    : 'Reinstalling app bundle from current repo source; the window will relaunch.';
  const posted = postNative('reinstallAppBundle', {
    request_id: requestId,
    resource_freshness: resourceFreshnessPayload(),
  });
  if (!posted) {
    reinstallRequestId = '';
    clearReinstallReceiptTimeout();
    clearReinstallRelaunchTimeout();
    setReinstallPending(false);
    els.status.textContent = 'Reinstall requires the macOS app. Open /Applications/Agent Trace Structurer.app and retry.';
    return;
  }
  clearReinstallReceiptTimeout();
  reinstallReceiptTimeout = window.setTimeout(() => {
    if (!reinstallInFlight || reinstallRequestId !== requestId) return;
    reinstallRequestId = '';
    clearReinstallRelaunchTimeout();
    setReinstallPending(false, 'failed');
    els.status.textContent = 'No native reinstall receipt arrived. Confirm the macOS app is active, then retry.';
  }, REINSTALL_RECEIPT_TIMEOUT_MS);
}

syncReinstallButtonState();

els.filename.value = defaultTraceFilename();
els.status.textContent = 'Waiting for clipboard.';
els.source.addEventListener('input', () => {
  currentGeneratedAt = null;
  els.status.textContent = els.source.value ? 'Preview updated.' : 'Waiting for clipboard.';
  render();
});
els.filename.addEventListener('input', render);
els.query.addEventListener('input', render);
els.buttons.toggleWatch?.addEventListener('click', () => {
  clipboardWatchEnabled = !clipboardWatchEnabled;
  postNative('clipboardControl', { enabled: clipboardWatchEnabled });
  renderWatchState();
});
els.buttons.openDownloads?.addEventListener('click', () => {
  if (!postNative('openDownloads')) {
    els.status.textContent = 'Open export folder is only available in the macOS app.';
  }
});
els.buttons.paste?.addEventListener('click', () => void pasteFromClipboard());
els.buttons.import?.addEventListener('click', () => els.file.click());
// Operator's "Find latest" workflow. Now binds to copyLatestClipboardClip
// (writes latest clipboard_history row's compressed file to NSPasteboard).
els.buttons.latest?.addEventListener('click', () => copyLatestClipboardClip());
els.buttons.operatorHud?.addEventListener('click', (event) => toggleWindowsPopup(event));
els.buttons.reinstallApp?.addEventListener('click', () => reinstallAppBundle());
els.buttons.promptHotkeys?.addEventListener('click', () => setPromptShelfHotkeysEnabled(!promptHotkeysEnabled));
els.buttons.minimizeBar?.addEventListener('click', (event) => {
  event.preventDefault();
  event.stopPropagation();
  collapseSystemBar('minimize');
});
els.buttons.copy?.addEventListener('click', () => void copyJson());
// Mission Rail v0 button bindings. These operate on the selected mission row,
// NOT on the global current packet / latest clipboard capture.
copyCompressedBtn?.addEventListener('click', () => copySelectedMissionArtifact('compressed'));
copyFullBtn?.addEventListener('click', () => copySelectedMissionArtifact('full'));
revealMissionBtn?.addEventListener('click', () => revealSelectedMission());
refreshMissionsBtn?.addEventListener('click', () => refreshMissionIndexClick());
// Startup: ask the native bridge for the current mission index. If the bridge
// is not present (e.g. served via http://localhost during dev), fall back to the
// read-only local server endpoint so browser verification still exercises rows.
requestMissionIndex();
requestPromptShelfHotkeyStatus();
els.buttons.download?.addEventListener('click', async () => {
  const result = await downloadJson(els.filename.value, currentPacket);
  addSavedCapture(result, currentPacket, currentPacket.capture_context?.capture_kind || 'manual', currentPacket.generated_at);
});
els.buttons.clear?.addEventListener('click', () => {
  currentGeneratedAt = null;
  els.source.value = '';
  els.status.textContent = 'Waiting for clipboard.';
  render();
});
els.buttons.clearHistory?.addEventListener('click', () => {
  savedCaptures = [];
  renderSavedCaptures();
  if (postNative('clearCaptureHistory')) {
    els.status.textContent = 'Clipboard capture history cleared.';
  } else {
    els.status.textContent = 'Local capture history cleared for this window.';
  }
});
toolbarDragHandle?.addEventListener('pointerdown', startToolbarDrag);
toolbarDragHandle?.addEventListener('click', pinSystemBar);
toolbarDragHandle?.addEventListener('dblclick', zoomWindowFromToolbar);
toolbarDragHandle?.addEventListener('pointercancel', (event) => endToolbarDrag(event, { force: true }));
toolbarDragHandle?.addEventListener('lostpointercapture', (event) => endToolbarDrag(event, { force: true }));
systemBarSurface?.addEventListener('pointerenter', handleSystemBarPointerEnter);
systemBarSurface?.addEventListener('pointerleave', handleSystemBarPointerLeave);
// Recovery hatch: clicking anywhere on the bar surface (not a button) pins.
// Without this, a stuck compact 76x76 icon has no path back to expanded
// because only the toolbar drag handle was wired to pinSystemBar.
systemBarSurface?.addEventListener('click', (event) => {
  if (interactiveSystemBarTarget(event.target)) return;
  pinSystemBar(event);
});
// Initialize the DOM state without expanding the native compact frame.
applySystemBarMode('init');
updateShellModeButton();
document.addEventListener('pointermove', moveToolbarDrag, { capture: true });
document.addEventListener('pointerup', endToolbarDrag, { capture: true });
window.addEventListener('pointerup', endToolbarDrag, { capture: true });
document.addEventListener('mouseup', () => endToolbarDrag(null, { force: true }), { capture: true });
window.addEventListener('blur', () => endToolbarDrag(null, { force: true }));
document.addEventListener('visibilitychange', () => {
  if (document.visibilityState !== 'visible') {
    endToolbarDrag(null, { force: true });
    return;
  }
  scheduleFocusMissionRefresh('page_visible_refresh');
});
window.addEventListener('focus', () => scheduleFocusMissionRefresh('window_focus_refresh'));
window.addEventListener('pageshow', () => scheduleFocusMissionRefresh('pageshow_refresh'));
window.addEventListener('keydown', (event) => {
  if (event.key === 'Escape' && windowsPopupOpen) {
    event.preventDefault();
    closeWindowsPopup('escape_key');
    return;
  }
  if (event.key === 'Escape' && systemBarExpanded) {
    if (activeDropdown) return;
    event.preventDefault();
    collapseSystemBar('escape');
  }
});
els.file.addEventListener('change', (event) => {
  void importFile(event.target.files?.[0]);
  event.target.value = '';
});
els.entityTabs.addEventListener('click', (event) => {
  const button = event.target.closest('[data-entity-group]');
  if (!button) return;
  activeEntityGroup = button.dataset.entityGroup;
  render();
});
els.savedList.addEventListener('click', (event) => {
  const exportButton = event.target.closest('[data-export-capture]');
  if (exportButton) {
    if (postNative('exportCapture', {
      stored_path: exportButton.dataset.storedPath || '',
      path: exportButton.dataset.exportPath || '',
      input_hash: exportButton.dataset.inputHash || '',
    })) {
      els.status.textContent = exportButton.dataset.exportPath
        ? 'Opening exported capture in Finder.'
        : 'Exporting capture to export folder.';
    }
    return;
  }
  const copy = event.target.closest('[data-copy-path]');
  if (copy) {
    void copyText(copy.dataset.copyPath);
  }
});

window.agentTraceStructurerDownloadFinished = (result) => {
  const pending = pendingNativeDownloads.get(result.request_id);
  if (!pending) return;
  pendingNativeDownloads.delete(result.request_id);
  if (result.ok) {
    pending.resolve(result);
  } else {
    pending.reject(new Error(result.error || 'Native download failed.'));
  }
};

window.agentTraceStructurerCaptureStored = (result) => {
  const pending = pendingNativeStores.get(result.request_id);
  if (!pending) return;
  pendingNativeStores.delete(result.request_id);
  if (result.ok) {
    pending.resolve(result);
  } else {
    pending.reject(new Error(result.error || 'Private capture store failed.'));
  }
};

window.agentTraceStructurerLatestReveal = (result) => {
  setLatestRevealPending(false);
  if (result.ok) {
    if (result.capture) rememberCapture(result.capture);
    els.status.textContent = 'Revealed latest.';
  } else {
    els.status.textContent = result.error || 'No saved capture file yet.';
  }
};

window.agentTraceStructurerOperatorHudResult = (result) => {
  operatorHudOpening = false;
  if (els.buttons.operatorHud) els.buttons.operatorHud.disabled = false;
  if (result.ok) {
    els.status.textContent = result.action === 'launched'
      ? 'Operator HUD opened.'
      : 'Operator HUD requested.';
  } else {
    els.status.textContent = result.error || 'Operator HUD launch failed.';
  }
};

window.agentTraceStructurerReinstallResult = (result) => {
  clearReinstallReceiptTimeout();
  const resultRequestId = result?.request_id ? String(result.request_id) : '';
  if (resultRequestId && reinstallRequestId && resultRequestId !== reinstallRequestId) return;
  if (result?.ok && result.stage === 'started') {
    if (resultRequestId) reinstallRequestId = resultRequestId;
    setReinstallPending(true, 'relaunching');
    els.status.textContent = 'Reinstall started; Agent Trace Structurer will relaunch.';
    armReinstallRelaunchWatchdog(false);
    return;
  }
  if (result?.ok && result.stage === 'installed') {
    if (resultRequestId) reinstallRequestId = resultRequestId;
    setReinstallPending(true, 'relaunching');
    els.status.textContent = 'Reinstall complete; relaunching Agent Trace Structurer.';
    armReinstallRelaunchWatchdog(true);
    return;
  }
  if (result?.ok) {
    setReinstallPending(true, 'relaunching');
    els.status.textContent = 'Reinstall complete; waiting for relaunch.';
    armReinstallRelaunchWatchdog(true);
    return;
  }
  reinstallRequestId = '';
  clearReinstallRelaunchTimeout();
  setReinstallPending(false, 'failed');
  els.status.textContent = `Reinstall failed: ${result?.error || result?.stage || 'unknown'}`;
};

// Prompt shelf workbar HUD — replaces the legacy Chrome operator HUD path.
window.agentTraceStructurerPromptShelfIndex = (payload) => {
  promptShelfIndex = normalizePromptShelfIndex(payload && typeof payload === 'object' ? payload : { ok: false, error: 'bad_payload' });
  updatePromptsSummary();
  if (activeDropdown === 'prompts' || isTracePromptsWorkbench(activeDropdown)) {
    guardAgentTraceAction('prompt_shelf_render', () => renderPromptsDropdown());
    if (dropdownEls.promptsReceipt && !promptCopyInFlight) {
      dropdownEls.promptsReceipt.textContent = promptShelfIndex.ok
        ? `${(promptShelfIndex.items || []).length} prompts · ${promptShelfIndex.items_dir || ''}`
        : `unavailable: ${promptShelfIndex.error || ''}`;
    }
  }
};

window.agentTraceStructurerPromptShelfCopy = (result) => {
  promptCopyInFlight = null;
  if (dropdownEls.promptsRows) {
    dropdownEls.promptsRows.querySelectorAll('[data-copying="true"]').forEach((node) => {
      delete node.dataset.copying;
    });
  }
  if (!dropdownEls.promptsReceipt) return;
  if (result && result.ok) {
    const slot = result.slot || '';
    const chars = Number(result.char_count || 0);
    const bytes = Number(result.byte_count || 0);
    const sha = result.sha16 || '';
    promptShelfLastCopiedSlot = slot;
    const traceScopeDefaulted = maybeDefaultTraceScopeForPromptShelf(slot);
    updatePromptUsageFromCopyResult(result);
    const uses = promptUsageCount(result.usage || { usage_count: result.usage_count });
    const useBit = uses > 0 ? ` · ${uses} uses` : '';
    const scopeBit = traceScopeDefaulted ? ` · Agent Trace scope=${traceScopeDefaulted}` : '';
    dropdownEls.promptsReceipt.textContent = `copied ${slot}${useBit} · ${chars}c · ${_formatKB(bytes)} · sha16=${sha}${scopeBit}`;
  } else {
    const err = (result && (result.error || result.stage)) || 'copy failed';
    dropdownEls.promptsReceipt.textContent = `copy failed: ${err}`;
  }
};

window.agentTraceStructurerPromptHotkeyStatus = (payload) => {
  applyPromptShelfHotkeyStatus(payload && typeof payload === 'object' ? payload : { ok: false, stage: 'bad_payload' });
};

window.agentTraceStructurerPromptHotkeyToggleResult = (payload) => {
  applyPromptShelfHotkeyStatus(payload && typeof payload === 'object' ? payload : { ok: false, stage: 'bad_payload' });
};

window.agentTraceStructurerChromeProfiles = (payload) => {
  chromeProfilesIndex = normalizeChromeProfilesIndex(payload && typeof payload === 'object' ? payload : { ok: false, error: 'bad_payload' });
  if (windowsPopupOpen) {
    renderChromeProfilesDropdown();
    if (dropdownEls.chromeProfilesReceipt && !chromeProfileOpenInFlight) {
      dropdownEls.chromeProfilesReceipt.textContent = chromeProfilesIndex.ok
        ? `${(chromeProfilesIndex.items || []).length} profiles · ${chromeProfilesIndex.chrome_user_data_dir || ''}`
        : `unavailable: ${chromeProfilesIndex.error || ''}`;
    }
  }
};

window.agentTraceStructurerOpenChromeProfileResult = (result) => {
  const openedProfile = chromeProfileOpenInFlight;
  chromeProfileOpenInFlight = '';
  if (dropdownEls.chromeProfileRows) {
    dropdownEls.chromeProfileRows.querySelectorAll('[data-opening="true"]').forEach((node) => {
      delete node.dataset.opening;
    });
  }
  if (!dropdownEls.chromeProfilesReceipt) return;
  if (result && result.ok) {
    const label = result.profile_name || result.profile_dir || openedProfile || 'Chrome profile';
    dropdownEls.chromeProfilesReceipt.textContent = `opened ${label} in Google Chrome`;
  } else {
    const err = (result && (result.error || result.stage)) || 'open failed';
    dropdownEls.chromeProfilesReceipt.textContent = `open failed: ${err}`;
  }
};

window.agentTraceStructurerOpenWebsiteResult = (result) => {
  chromeWebsiteOpenInFlight = false;
  if (dropdownEls.chromeProfileRows) {
    dropdownEls.chromeProfileRows.querySelectorAll('[data-window-action="website"][data-opening="true"]').forEach((node) => {
      delete node.dataset.opening;
    });
  }
  if (!dropdownEls.chromeProfilesReceipt) return;
  if (result && result.ok) {
    dropdownEls.chromeProfilesReceipt.textContent = 'opened Microcosm site in Google Chrome';
  } else {
    const err = (result && (result.error || result.stage)) || 'open failed';
    dropdownEls.chromeProfilesReceipt.textContent = `website open failed: ${err}`;
  }
};

window.agentTraceStructurerClipboardChanged = (payload) => {
  void handleClipboardText(payload);
};

const nativeClipboardChunkTransfers = new Map();

window.agentTraceStructurerClipboardChunkStart = (payload) => {
  const transferId = payload?.transfer_id || '';
  if (!transferId) return;
  nativeClipboardChunkTransfers.set(transferId, {
    payload: { ...payload, text: '' },
    chunks: new Array(Number(payload.chunk_count || 0)).fill(''),
    received: 0,
  });
  rememberClipboardSnapshot(payload, { flash: true });
  els.status.textContent = `Receiving large clipboard capture (${_formatKB(payload.source_bytes || payload.bytes || 0)}).`;
};

window.agentTraceStructurerClipboardChunkAppend = (payload) => {
  const transferId = payload?.transfer_id || '';
  const transfer = nativeClipboardChunkTransfers.get(transferId);
  if (!transfer) return;
  const index = Number(payload.index);
  if (!Number.isInteger(index) || index < 0 || index >= transfer.chunks.length) return;
  if (!transfer.chunks[index]) transfer.received += 1;
  transfer.chunks[index] = String(payload.text || '');
  if (transfer.received % 8 === 0 || transfer.received === transfer.chunks.length) {
    els.status.textContent = `Receiving large clipboard capture (${transfer.received}/${transfer.chunks.length}).`;
  }
};

window.agentTraceStructurerClipboardChunkFinish = (payload) => {
  const transferId = payload?.transfer_id || '';
  const transfer = nativeClipboardChunkTransfers.get(transferId);
  if (!transfer) return;
  nativeClipboardChunkTransfers.delete(transferId);
  const text = transfer.chunks.join('');
  void handleClipboardText({
    ...transfer.payload,
    text,
    chars: text.length,
    chunked: true,
  });
};

window.agentTraceStructurerClipboardChunkError = (payload) => {
  const transferId = payload?.transfer_id || '';
  if (transferId) nativeClipboardChunkTransfers.delete(transferId);
  els.status.textContent = `Large clipboard transfer failed: ${payload?.error || 'unknown error'}`;
};

window.agentTraceStructurerClipboardSnapshot = (payload) => {
  rememberClipboardSnapshot(payload);
};

window.agentTraceStructurerNativeState = (state) => {
  nativeState = { ...nativeState, ...state };
  if (typeof state.presentation_mode === 'string') {
    document.body.dataset.nativeShellMode = state.presentation_mode === 'window' ? 'window' : 'floating';
    if (state.presentation_mode === 'window' && typeof state.window_mode !== 'string') {
      syncNativeWindowMode('window', 'native_presentation');
    }
  }
  if (typeof state.window_mode === 'string') {
    syncNativeWindowMode(state.window_mode, 'native_state');
  }
  if (typeof state.clipboard_watching === 'boolean') {
    clipboardWatchEnabled = state.clipboard_watching;
  }
  if (Array.isArray(state.capture_history)) {
    hydrateCaptureHistory(state.capture_history);
  }
  renderSaveTarget();
};

window.agentTraceStructurerCaptureHistory = (payload) => {
  if (Array.isArray(payload?.capture_history)) {
    hydrateCaptureHistory(payload.capture_history);
  }
  if (payload?.history_path) {
    nativeState.history_path = payload.history_path;
  }
};

renderSaveTarget();
renderSavedCaptures();
render();
window.setTimeout(() => {
  postNative('requestCaptureHistory');
  postNative('requestPromptShelfIndex');
}, 0);
window.setInterval(renderTopSummary, 1000);

// ============================================================
// Dropdown Architecture v0 — closed capsule with Latest Clip ▾ and Agent Trace ▾
// triggers; click → opens panel below; Swift resizes window via setSystemBarFrame.
// Row click SELECTS only (does not copy). Primary action uses the existing
// verified bridges (copyLatestClipboardClip / copyLatestMissionTrace).
// ============================================================
dropdownEls = {
  latestClipTrigger: document.getElementById('latest-clip-trigger'),
  agentTraceTrigger: document.getElementById('agent-trace-trigger'),
  promptsTrigger: document.getElementById('prompts-trigger'),
  latestClipSummary: document.getElementById('latest-clip-summary'),
  agentTraceSummary: document.getElementById('agent-trace-summary'),
  promptsSummary: document.getElementById('prompts-summary'),
  promptsView: document.getElementById('dropdown-prompts'),
  promptsRows: document.getElementById('prompts-rows'),
  promptsReceipt: document.getElementById('prompts-receipt'),
  promptsRefresh: document.getElementById('prompts-refresh'),
  promptsShell: document.getElementById('prompts-shell'),
  promptsHome: document.getElementById('dropdown-prompts'),
  windowsPopup: document.getElementById('windows-popup'),
  chromeProfileRows: document.getElementById('chrome-profile-rows'),
  chromeProfilesReceipt: document.getElementById('chrome-profiles-receipt'),
  chromeProfilesRefresh: document.getElementById('chrome-profiles-refresh'),
  workbenchPromptsSlot: document.getElementById('workbench-prompts-slot'),
  panel: document.getElementById('systembar-dropdown'),
  clipboardView: document.getElementById('dropdown-clipboard'),
  agentTraceView: document.getElementById('dropdown-agent-trace'),
  clipboardRows: document.getElementById('clipboard-rows'),
  agentTraceRows: document.getElementById('agent-trace-rows'),
  agentTraceSelectedBrief: document.getElementById('agent-trace-selected-brief'),
  agentTraceMissionCounts: document.getElementById('agent-trace-mission-counts'),
  agentTraceSearchProvenance: document.getElementById('agent-trace-search-provenance'),
  agentTraceDetail: document.getElementById('agent-trace-detail'),
  agentTraceSort: document.getElementById('agent-trace-sort'),
  agentTraceSearch: document.getElementById('agent-trace-search'),
  agentTraceRefresh: document.getElementById('agent-trace-refresh'),
  clipboardCopyLatest: document.getElementById('clipboard-copy-latest'),
  clipboardCopyFull: document.getElementById('clipboard-copy-full'),
  clipboardReveal: document.getElementById('clipboard-reveal'),
  clipboardReceipt: document.getElementById('clipboard-receipt'),
  missionCaptureCopy: document.getElementById('mission-capture-copy'),
  missionPaneCopyCapsule: document.getElementById('mission-pane-copy-capsule'),
  missionPaneCopyCloseout: document.getElementById('mission-pane-copy-closeout'),
  missionPaneSaveReveal: document.getElementById('mission-pane-save-reveal'),
  missionPanePin: document.getElementById('mission-pane-pin'),
  missionPaneSnooze: document.getElementById('mission-pane-snooze'),
  missionPaneReviewed: document.getElementById('mission-pane-reviewed'),
  missionPaneRefresh: document.getElementById('mission-pane-refresh'),
  missionPaneToggleInactive: document.getElementById('mission-pane-toggle-inactive'),
  missionSourceWindow: document.getElementById('mission-source-window'),
  missionScopeContract: document.getElementById('mission-source-scope-contract'),
  missionCopyTape: document.getElementById('mission-copy-tape'),
  missionCopyCompact: document.getElementById('mission-copy-compact'),
  missionCopyCloseout: document.getElementById('mission-copy-closeout'),
  missionCopyFull: document.getElementById('mission-copy-full'),
  missionDownloadDenoised: document.getElementById('mission-download-denoised'),
  missionDownloadTape: document.getElementById('mission-download-tape'),
  missionDownloadCompact: document.getElementById('mission-download-compact'),
  missionDownloadFull: document.getElementById('mission-download-full'),
  missionReveal: document.getElementById('mission-reveal'),
  agentTraceCompact: document.getElementById('agent-trace-compact'),
  // v6 variant catalog table cells.
  variantStateDenoised: document.getElementById('variant-state-denoised'),
  variantStateTape: document.getElementById('variant-state-tape'),
  variantStateCompact: document.getElementById('variant-state-compact'),
  variantStateFull: document.getElementById('variant-state-full'),
  variantStateRaw: document.getElementById('variant-state-raw'),
  variantBytesDenoised: document.getElementById('variant-bytes-denoised'),
  variantBytesTape: document.getElementById('variant-bytes-tape'),
  variantBytesCompact: document.getElementById('variant-bytes-compact'),
  variantBytesFull: document.getElementById('variant-bytes-full'),
  variantBytesRaw: document.getElementById('variant-bytes-raw'),
  missionReceipt: document.getElementById('mission-receipt'),
};
// activeDropdown is declared at module top (line ~53) for TDZ safety;
// keep this line as a re-assignment to preserve the original init order.
activeDropdown = null;
attachMissionRowsResizeObserver();
if (windowShellDefaultDropdownPending || isWindowShellMode()) {
  window.setTimeout(() => ensureWindowShellWorkbench(activeDropdown || 'agent_trace'), 0);
}
if (isStandaloneBrowserRuntime()) {
  window.setTimeout(() => ensureStandaloneBrowserWorkbench(activeDropdown || 'agent_trace'), 0);
}
// Prompt shelf cache populated by Swift handler `requestPromptShelfIndex`.
// Mirrors the shape emitted by `tools/agent_trace_structurer/prompt_shelf_helper.py --list`.
let promptShelfIndex = null;
let promptCopyInFlight = null;
let promptShelfLastCopiedSlot = '';
let chromeProfilesIndex = null;
let chromeProfileOpenInFlight = '';
let chromeWebsiteOpenInFlight = false;
let windowsPopupOpen = false;
const EXPANDED_BAR_HEIGHT = 80;
const EXPANDED_BAR_WIDTH = 980;
const WINDOWS_POPUP_HEIGHT = 300;
// v4: browser shell needs a usable height, not a clipped strip. Bumped
// 460→720 so the action shelf, mission list, and selected-mission
// variant rows all fit without horizontal/vertical scroll inside the
// dropdown panel.
const DROPDOWN_HEIGHT = 720;
const FULL_JSON_MANIFEST_THRESHOLD = 512 * 1024;

function _escHtml(s) {
  return String(s ?? '').replace(/[&<>"']/g, (c) => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}
function _formatKB(bytes) {
  if (!bytes || bytes <= 0) return '—';
  const kb = bytes / 1024;
  return kb >= 1000 ? `${(kb / 1024).toFixed(1)} MB` : `${kb < 10 ? kb.toFixed(1) : Math.round(kb)} KB`;
}
function _formatExactSize(bytes) {
  const n = Number(bytes || 0);
  if (!Number.isFinite(n) || n <= 0) return '—';
  return `${_formatKB(n)} · ${Math.round(n).toLocaleString()} bytes`;
}
function _traceCapsuleSizeLabel(artifact, currentness) {
  const bytes = Number(artifact?.bytes || 0);
  if (!bytes) return 'Copy file: will measure after prepare';
  const prefix = 'Copy file';
  if (currentness && !currentness.ready) {
    const reason = String(currentness.reason || '');
    const identityMismatch = /schema_mismatch|artifact_role_mismatch|source_window_mismatch|prompt_mismatch|turn_mismatch|empty_trace/.test(reason);
    if (identityMismatch) return 'Copy file: will measure after prepare';
    return `${prefix}: ${_formatExactSize(bytes)} · will refresh on next copy`;
  }
  return `${prefix}: ${_formatExactSize(bytes)}`;
}
function artifactPathFromCapture(data) {
  return data?.artifact_path
    || data?.variant_artifact?.path
    || data?.variant_artifact?.artifact_path
    || data?.download?.path
    || '';
}
function sourceClipPathFromCapture(data) {
  return data?.source_clip_path
    || data?.clip_path
    || data?.variant_artifact?.source_clip_path
    || data?.variant_artifact?.clip_path
    || '';
}
function missionCopyCallbackMismatch(data, anchor) {
  if (!data?.ok || !anchor) return '';
  const dataKey = data?.mission_key || missionKeyFromParts(data?.ui_provider || data?.provider, data?.session_id);
  if (anchor.key && dataKey && dataKey !== anchor.key) {
    return `copy callback mission mismatch: expected ${anchor.key}, got ${dataKey}`;
  }
  const expectedWindow = normalizeTraceSourceWindow(anchor.copiedSourceWindow || '');
  const actualWindow = normalizeTraceSourceWindow(data.ui_source_window || data.source_window || '');
  if (expectedWindow && actualWindow && expectedWindow !== actualWindow) {
    return `copy callback source-window mismatch: expected ${expectedWindow}, got ${actualWindow}`;
  }
  return '';
}
function postSetSystemBarFrame(h, w = null) {
  if (isWindowShellMode()) return;
  const payload = { height: h };
  if (Number.isFinite(w) && w > 0) payload.width = w;
  postNative('setSystemBarFrame', payload);
}

function ensureWindowShellWorkbench(kind = 'agent_trace') {
  if (!isWindowShellMode()) return;
  const target = kind || activeDropdown || 'agent_trace';
  if (!dropdownEls?.panel) {
    windowShellDefaultDropdownPending = true;
    return;
  }
  windowShellDefaultDropdownPending = false;
  if (activeDropdown !== target || dropdownEls.panel.hidden) {
    openDropdown(target);
  }
}

function ensureStandaloneBrowserWorkbench(kind = 'agent_trace') {
  if (!isStandaloneBrowserRuntime() || !dropdownEls?.panel) return false;
  document.body.dataset.nativeShellMode = 'window';
  syncNativeWindowMode('window', 'standalone_browser_boot');
  ensureWindowShellWorkbench(kind || activeDropdown || 'agent_trace');
  return true;
}

function isTracePromptsWorkbench(kind = activeDropdown) {
  return isWindowShellMode() && (kind === 'agent_trace' || kind === 'prompts');
}

function effectiveDropdownKind(kind = 'agent_trace') {
  return isTracePromptsWorkbench(kind) ? 'agent_trace' : kind;
}

function dropdownPanelMode(kind = activeDropdown) {
  return isTracePromptsWorkbench(kind) ? 'agent_trace_prompts' : effectiveDropdownKind(kind);
}

function isAgentTraceWorkbenchActive(kind = activeDropdown) {
  const mode = dropdownEls?.panel?.dataset?.mode || '';
  return kind === 'agent_trace' || mode === 'agent_trace' || mode === 'agent_trace_prompts';
}

function placePromptsSurface(dockInWorkbench) {
  const shell = dropdownEls?.promptsShell;
  const home = dropdownEls?.promptsHome;
  const slot = dropdownEls?.workbenchPromptsSlot;
  if (!shell || !home || !slot) return;
  if (dockInWorkbench) {
    if (shell.parentElement !== slot) slot.appendChild(shell);
    slot.hidden = false;
  } else {
    if (shell.parentElement !== home) home.appendChild(shell);
    slot.hidden = true;
  }
}

function openDropdown(kind) {
  const target = effectiveDropdownKind(kind || 'agent_trace');
  const combinedTracePrompts = isTracePromptsWorkbench(kind || target);
  closeWindowsPopup('open_dropdown', { preserveFrame: true });
  clearSystemBarCollapseTimer();
  clearSystemBarCompactHoverTimer();
  systemBarPinned = true;
  systemBarHover = true;
  systemBarExpanded = true;
  document.body.dataset.systembarExpanded = 'true';
  document.body.dataset.systembarPinned = 'true';
  document.body.dataset.systembarMode = 'pinned';
  document.body.dataset.nativeWindowMode = isWindowShellMode() ? 'window' : 'expanded';
  document.body.dataset.systembarContent = 'visible';
  systemBarLastMode = 'expanded';
  activeDropdown = target;
  dropdownEls.panel.hidden = false;
  dropdownEls.panel.dataset.mode = dropdownPanelMode(kind || target);
  placePromptsSurface(combinedTracePrompts);
  dropdownEls.clipboardView.hidden = target !== 'clipboard';
  dropdownEls.agentTraceView.hidden = target !== 'agent_trace';
  if (dropdownEls.promptsView) dropdownEls.promptsView.hidden = combinedTracePrompts || target !== 'prompts';
  dropdownEls.latestClipTrigger.setAttribute('aria-expanded', target === 'clipboard' ? 'true' : 'false');
  dropdownEls.agentTraceTrigger.setAttribute('aria-expanded', target === 'agent_trace' ? 'true' : 'false');
  dropdownEls.promptsTrigger?.setAttribute('aria-expanded', (combinedTracePrompts || target === 'prompts') ? 'true' : 'false');
  els.buttons.operatorHud?.setAttribute('aria-expanded', 'false');
  // Hide legacy section.main (Trace input / Structured packet / Timeline
  // cards) so they cannot bleed through the expanded native window. CSS
  // rule: body[data-dropdown-active="true"] section.main { display: none }.
  document.body.dataset.dropdownActive = 'true';
  if (target === 'clipboard') renderClipboardDropdown();
  if (target === 'agent_trace') {
    safeRenderAgentTraceDropdown('open_dropdown');
    scheduleFocusMissionRefresh('workbench_open_refresh');
  }
  if (combinedTracePrompts || target === 'prompts') guardAgentTraceAction('prompt_shelf_render', () => renderPromptsDropdown());
  postSetSystemBarFrame(DROPDOWN_HEIGHT, EXPANDED_BAR_WIDTH);
}
// v10 hard-gated close: every collapse path must pass an explicit reason
// so we can audit unknown callers via window.__aiwSystemBar.closeCallLog.
// Anything not in the allowed reason set still closes (so we don't break
// existing flows) but is recorded for diagnostic review.
const _closeCallLog = [];
const _CLOSE_REASONS_ALLOWED = new Set([
  'compact_button',
  'escape_key',
  'trigger_toggle',
  'outside_click',
  'force_open_snapshot_cleanup',
  'explicit_api',
]);
function closeDropdown(reason) {
  const why = reason || 'unknown';
  const closingDropdown = activeDropdown;
  clearSystemBarCollapseTimer();
  clearSystemBarCompactHoverTimer();
  const stack = (new Error()).stack || '';
  _closeCallLog.push({ at: Date.now(), reason: why, stack: stack.split('\n').slice(0, 4).join(' | ') });
  if (_closeCallLog.length > 24) _closeCallLog.shift();
  if (!_CLOSE_REASONS_ALLOWED.has(why)) {
    try { console.warn('[closeDropdown] called with unknown reason:', why, stack); } catch (_) {}
  }
  if (isWindowShellMode()) {
    openDropdown(closingDropdown || 'agent_trace');
    return;
  }
  if (closingDropdown === 'agent_trace') {
    clearMissionFinishedAutoRefresh();
    clearMissionTitleAuthoritySync();
  }
  activeDropdown = null;
  dropdownEls.panel.hidden = true;
  dropdownEls.panel.dataset.mode = '';
  placePromptsSurface(false);
  dropdownEls.latestClipTrigger.setAttribute('aria-expanded', 'false');
  dropdownEls.agentTraceTrigger.setAttribute('aria-expanded', 'false');
  dropdownEls.promptsTrigger?.setAttribute('aria-expanded', 'false');
  els.buttons.operatorHud?.setAttribute('aria-expanded', 'false');
  document.body.dataset.dropdownActive = 'false';
  if (isWindowShellMode()) {
    systemBarPinned = true;
    systemBarHover = true;
    systemBarExpanded = true;
    document.body.dataset.systembarExpanded = 'true';
    document.body.dataset.systembarPinned = 'true';
    document.body.dataset.systembarMode = 'pinned';
    document.body.dataset.systembarContent = 'visible';
    systemBarLastMode = 'window';
    return;
  }
  if (why === 'compact_button' || why === 'escape_key' || why === 'force_open_snapshot_cleanup') {
    systemBarPinned = false;
    systemBarHover = false;
    systemBarExpanded = false;
    document.body.dataset.systembarExpanded = 'false';
    document.body.dataset.systembarPinned = 'false';
    document.body.dataset.systembarMode = 'compact';
    hideSystemBarContent();
    postNative('setWindowMode', {
      mode: 'compact',
      pinned: false,
      reason: `${why}:${closingDropdown || 'dropdown'}`,
    });
    systemBarLastMode = 'compact';
    return;
  }
  postSetSystemBarFrame(EXPANDED_BAR_HEIGHT, EXPANDED_BAR_WIDTH);
}

function openWindowsPopup() {
  clearSystemBarCollapseTimer();
  clearSystemBarCompactHoverTimer();
  systemBarPinned = true;
  systemBarHover = true;
  systemBarExpanded = true;
  document.body.dataset.systembarExpanded = 'true';
  document.body.dataset.systembarPinned = 'true';
  document.body.dataset.systembarMode = 'pinned';
  document.body.dataset.nativeWindowMode = isWindowShellMode() ? 'window' : 'expanded';
  document.body.dataset.systembarContent = 'visible';
  systemBarLastMode = 'expanded';
  windowsPopupOpen = true;
  if (dropdownEls.windowsPopup) dropdownEls.windowsPopup.hidden = false;
  els.buttons.operatorHud?.setAttribute('aria-expanded', 'true');
  renderChromeProfilesDropdown();
  if (!isWindowShellMode() && !activeDropdown) {
    postSetSystemBarFrame(WINDOWS_POPUP_HEIGHT, EXPANDED_BAR_WIDTH);
  }
}

function closeWindowsPopup(reason = 'explicit', options = {}) {
  if (!windowsPopupOpen) return;
  windowsPopupOpen = false;
  if (dropdownEls?.windowsPopup) dropdownEls.windowsPopup.hidden = true;
  els.buttons.operatorHud?.setAttribute('aria-expanded', 'false');
  if (!options.preserveFrame && !activeDropdown && !isWindowShellMode()) {
    postSetSystemBarFrame(EXPANDED_BAR_HEIGHT, EXPANDED_BAR_WIDTH);
  }
}

function toggleWindowsPopup(event) {
  event?.preventDefault?.();
  event?.stopPropagation?.();
  if (windowsPopupOpen) {
    closeWindowsPopup('trigger_toggle');
    return;
  }
  openWindowsPopup();
}

function toggleDropdown(kind) {
  // v10 functional rule: the workbench (agent_trace) is a sticky surface,
  // not a popover. Once opened it must only close via ← Compact or Esc.
  // The trigger summary now mirrors the selected mission title, which
  // made operators confuse the closed-bar trigger with a workbench row;
  // clicking the trigger thinking it was a row collapsed everything.
  // Trigger now only opens — never re-toggles closed.
  const target = effectiveDropdownKind(kind);
  if (activeDropdown === target) {
    if (kind === 'agent_trace') return;
    if (isWindowShellMode()) return;  // sticky workbench
    closeDropdown('trigger_toggle');
    return;
  }
  openDropdown(kind);
}
dropdownEls.latestClipTrigger?.addEventListener('click', () => toggleDropdown('clipboard'));
dropdownEls.agentTraceTrigger?.addEventListener('click', () => toggleDropdown('agent_trace'));
dropdownEls.promptsTrigger?.addEventListener('click', () => toggleDropdown('prompts'));
document.getElementById('shell-mode-toggle')?.addEventListener('click', toggleShellMode);
document.addEventListener('pointerdown', (event) => {
  if (!windowsPopupOpen) return;
  if (event.target?.closest?.('#windows-popup') || event.target?.closest?.('#operator-hud')) return;
  closeWindowsPopup('outside_click');
}, { capture: true });
dropdownEls.promptsRefresh?.addEventListener('click', () => guardAgentTraceAction('prompt_refresh', () => {
  promptShelfIndex = null;
  if (dropdownEls.promptsReceipt) dropdownEls.promptsReceipt.textContent = 'refreshing…';
  postNative('requestPromptShelfIndex');
}));
dropdownEls.promptsRows?.addEventListener('click', (event) => guardAgentTraceAction('prompt_shelf_click', () => {
  const row = event.target?.closest?.('[data-prompt-slot]');
  if (!row) return;
  const slot = row.getAttribute('data-prompt-slot') || '';
  if (!slot) return;
  if (promptCopyInFlight) return;
  const item = findPromptShelfItem(slot) || {};
  promptCopyInFlight = slot;
  row.dataset.copying = 'true';
  if (dropdownEls.promptsReceipt) dropdownEls.promptsReceipt.textContent = `copying ${slot}…`;
  postNative('copyPromptShelfPrompt', {
    slot,
    label: item.label || '',
    title: item.title || '',
    slug: item.slug || '',
    item_path: item.item_path || '',
  });
}));
dropdownEls.chromeProfilesRefresh?.addEventListener('click', () => {
  chromeProfilesIndex = null;
  if (dropdownEls.chromeProfilesReceipt) dropdownEls.chromeProfilesReceipt.textContent = 'refreshing…';
  renderChromeProfilesDropdown();
});
dropdownEls.chromeProfileRows?.addEventListener('click', (event) => {
  const websiteRow = event.target?.closest?.('[data-window-action="website"]');
  if (websiteRow) {
    if (chromeWebsiteOpenInFlight) return;
    chromeWebsiteOpenInFlight = true;
    websiteRow.dataset.opening = 'true';
    if (dropdownEls.chromeProfilesReceipt) dropdownEls.chromeProfilesReceipt.textContent = 'opening Microcosm site in Google Chrome…';
    const posted = postNative('openMicrocosmWebsite');
    if (!posted) {
      chromeWebsiteOpenInFlight = false;
      delete websiteRow.dataset.opening;
      if (dropdownEls.chromeProfilesReceipt) dropdownEls.chromeProfilesReceipt.textContent = 'native bridge unavailable';
    }
    return;
  }
  const row = event.target?.closest?.('[data-profile-dir]');
  if (!row) return;
  const profileDir = row.getAttribute('data-profile-dir') || '';
  if (!profileDir || chromeProfileOpenInFlight) return;
  const item = findChromeProfileItem(profileDir) || {};
  chromeProfileOpenInFlight = profileDir;
  row.dataset.opening = 'true';
  if (dropdownEls.chromeProfilesReceipt) dropdownEls.chromeProfilesReceipt.textContent = `opening ${item.name || profileDir}…`;
  const posted = postNative('openChromeProfile', {
    profile_dir: profileDir,
    profile_name: item.name || '',
  });
  if (!posted) {
    chromeProfileOpenInFlight = '';
    delete row.dataset.opening;
    if (dropdownEls.chromeProfilesReceipt) dropdownEls.chromeProfilesReceipt.textContent = 'native bridge unavailable';
  }
});

function updateLatestClipSummary() {
  const row = (savedCaptures && savedCaptures[0]) || null;
  if (!row) { dropdownEls.latestClipSummary.textContent = 'no captures'; return; }
  const kind = (row.kind || 'capture').replace(/_/g, ' ');
  const bytes = row.contentBytes || row.bytes || row.chars || 0;
  dropdownEls.latestClipSummary.textContent = `${kind} · ${_formatKB(bytes)}`;
}
// v7 vocabulary: artifact_freshness.state speaks about the DERIVED
// artifact (trace packet), not the raw provider source. When the row
// has a latest_completed_turn the raw source IS available — the
// derived artifact may just be 'pending materialization'. Don't tell
// the operator NEEDS CAPTURE row-wide when the raw trace is current.
function _freshLabel(state, reason, hasTraceTurn, sourceState = '', activeTrace = false) {
  if (activeTrace && ['source_newer_than_index', 'source_size_changed'].includes(sourceState)) return { text: 'LIVE SOURCE', cls: 'current' };
  if (['source_newer_than_index', 'source_size_changed'].includes(sourceState)) return { text: 'STALE INDEX', cls: 'stale' };
  if (sourceState === 'source_missing') return { text: 'SOURCE MISSING', cls: 'capture-failed' };
  if (state === 'current') return { text: 'READY', cls: 'current' };
  if (state === 'stale') return { text: 'STALE', cls: 'stale' };
  if (state === 'partial_only') return { text: 'PARTIAL', cls: 'partial' };
  if (state === 'missing') {
    if (reason === 'capture_failed') return { text: 'CAPTURE FAILED', cls: 'capture-failed' };
    // Raw provider source exists; derived artifact is just preparable.
    if (hasTraceTurn) return { text: activeTrace ? 'SOURCE LIVE' : 'SOURCE READY', cls: activeTrace ? 'current' : 'needs-capture' };
    return { text: 'NO TURN', cls: 'partial' };
  }
  return { text: (state || 'UNKNOWN').toUpperCase(), cls: 'unknown' };
}
function updateAgentTraceSummary() {
  if (isResourceBundleStale()) {
    dropdownEls.agentTraceSummary.textContent = 'STALE BUNDLE · reinstall app';
    return;
  }
  const row = findMissionByKey(selectedMissionKey) || (sortedMissionRows(activeMissionRows())[0] || null);
  const goalSummary = missionGoalSummaryText();
  if (!row) {
    dropdownEls.agentTraceSummary.textContent = ['no missions', goalSummary].filter(Boolean).join(' · ');
    return;
  }
  const fresh = (row.artifact_freshness || {}).state || 'unknown';
  const reason = (row.artifact_freshness || {}).reason || '';
  const displayTurn = activityDisplayTurn(row);
  const hasTurn = displayTurn.turn_index != null;
  const activeTrace = rowHasActiveTrace(row);
  const flabel = _freshLabel(fresh, reason, hasTurn, sourceFreshnessState(row), activeTrace);
  const label = missionWorkflowPill(row, missionViewStateForRow(row), flabel).text.toLowerCase();
  const turnStr = hasTurn ? ` · ${activeTrace ? 'active' : 'latest'} #${displayTurn.turn_index}` : '';
  const scope = traceScopeMetrics(row, selectedTraceSourceWindow(), displayTurn);
  dropdownEls.agentTraceSummary.textContent = [
    providerShortBadge(row.provider),
    missionDisplayTitle(row, displayTurn),
    `${label}${turnStr}`,
    scope.label,
    goalSummary,
  ].filter(Boolean).join(' · ');
}

function promptUsageCount(item) {
  const count = Number(item?.usage_count ?? item?.count ?? 0);
  if (!Number.isFinite(count) || count < 0) return 0;
  return Math.floor(count);
}

function sortPromptShelfItems(items) {
  return [...items].map((item, index) => ({
    ...item,
    _promptShelfSourceOrder: Number.isFinite(Number(item._promptShelfSourceOrder))
      ? Number(item._promptShelfSourceOrder)
      : index,
  })).sort((left, right) => {
    const countDelta = promptUsageCount(right) - promptUsageCount(left);
    if (countDelta !== 0) return countDelta;
    return left._promptShelfSourceOrder - right._promptShelfSourceOrder;
  });
}

function normalizePromptShelfIndex(payload) {
  const normalized = payload && typeof payload === 'object' ? { ...payload } : { ok: false, error: 'bad_payload' };
  if (normalized.ok && Array.isArray(normalized.items)) {
    normalized.items = sortPromptShelfItems(normalized.items);
    normalized.sort = normalized.sort || 'usage_count_desc';
  }
  return normalized;
}

function findPromptShelfItem(slot) {
  const wanted = String(slot || '').toLowerCase();
  if (!wanted || !promptShelfIndex?.items) return null;
  return promptShelfIndex.items.find((item) => {
    return [item.slot, item.label, item.slug].some((value) => String(value || '').toLowerCase() === wanted);
  }) || null;
}

function promptShelfConsumerForSlot(slot) {
  const value = String(slot || '').trim().toLowerCase();
  if (value === 'b2' || value.includes('continue intelligently')) return 'type_b_continue';
  if (value === 'b2.2' || value.includes('semantic carryforward')) return 'type_b_semantic_carryforward';
  if (value === 'b2.3' || value.includes('visual refinement')) return 'type_b_visual_refinement';
  if (value === 'b3' || value.includes('context compaction')) return 'compact';
  if (value === 'b4' || value.includes('clarity')) return 'raw_debug';
  return '';
}

function maybeDefaultTraceScopeForPromptShelf(slot) {
  const consumer = promptShelfConsumerForSlot(slot);
  if (!['type_b_continue', 'type_b_semantic_carryforward', 'type_b_visual_refinement', 'compact'].includes(consumer)) return '';
  const row = findMissionByKey(selectedMissionKey);
  if (!row) return '';
  if (consumer === 'compact') {
    const compact = traceScopeMetrics(row, SOURCE_WINDOW_FULL_THREAD_CONCISE);
    if (!(Number(compact.fullTurnCount || 0) > 1) || !(compact.estimatedBytes > 0)) return '';
    window.__aiwTraceSourceWindow = SOURCE_WINDOW_FULL_THREAD_CONCISE;
    if (dropdownEls?.missionSourceWindow) dropdownEls.missionSourceWindow.value = SOURCE_WINDOW_FULL_THREAD_CONCISE;
    if (isAgentTraceWorkbenchActive()) safeRenderAgentTraceDropdown('prompt_shelf_compact_scope_default');
    updateAgentTraceSummary();
    return 'full_thread_concise';
  }
  const detailed = traceScopeMetrics(row, SOURCE_WINDOW_FULL_THREAD);
  const traceBudget = VARIANT_SIZE_BUDGETS.trace_capsule || Infinity;
  if (!(Number(detailed.fullTurnCount || 0) > 1) || !(detailed.estimatedBytes > 0) || detailed.estimatedBytes > traceBudget) {
    return '';
  }
  window.__aiwTraceSourceWindow = SOURCE_WINDOW_FULL_THREAD;
  if (dropdownEls?.missionSourceWindow) dropdownEls.missionSourceWindow.value = SOURCE_WINDOW_FULL_THREAD;
  if (isAgentTraceWorkbenchActive()) safeRenderAgentTraceDropdown('prompt_shelf_type_b_scope_default');
  updateAgentTraceSummary();
  return 'full_thread';
}

function updatePromptUsageFromCopyResult(result) {
  if (!promptShelfIndex?.items || !result?.slot) return;
  const usage = result.usage && typeof result.usage === 'object' ? result.usage : {};
  const slot = String(result.slot || '');
  promptShelfIndex.usage_total_copies = Math.max(
    Number(promptShelfIndex.usage_total_copies || 0) + 1,
    promptUsageCount(usage)
  );
  promptShelfIndex.usage_prompt_count = Math.max(Number(promptShelfIndex.usage_prompt_count || 0), 1);
  promptShelfIndex.items = promptShelfIndex.items.map((item) => {
    const matchesSlot = [item.slot, item.label, item.slug].some((value) => String(value || '').toLowerCase() === slot.toLowerCase());
    if (!matchesSlot) return item;
    return {
      ...item,
      usage_count: promptUsageCount(usage) || promptUsageCount(result),
      first_copied_at: usage.first_copied_at || item.first_copied_at,
      last_copied_at: usage.last_copied_at || item.last_copied_at,
    };
  });
  promptShelfIndex.items = sortPromptShelfItems(promptShelfIndex.items);
  updatePromptsSummary();
  renderPromptsDropdown();
}

function updatePromptsSummary() {
  if (!dropdownEls.promptsSummary) return;
  if (promptShelfIndex == null) {
    dropdownEls.promptsSummary.textContent = 'loading…';
    return;
  }
  if (!promptShelfIndex.ok) {
    dropdownEls.promptsSummary.textContent = 'unavailable';
    return;
  }
  const count = (promptShelfIndex.items || []).length;
  const totalCopies = Number(promptShelfIndex.usage_total_copies || 0);
  dropdownEls.promptsSummary.textContent = count === 0
    ? 'no prompts'
    : totalCopies > 0
      ? `${count} prompts · by use`
      : `${count} prompts`;
}

function normalizeChromeProfilesIndex(payload) {
  const normalized = payload && typeof payload === 'object' ? { ...payload } : { ok: false, error: 'bad_payload' };
  if (Array.isArray(normalized.items)) {
    normalized.items = normalized.items.map((item) => ({ ...(item || {}) }));
  } else {
    normalized.items = [];
  }
  return normalized;
}

function findChromeProfileItem(profileDir) {
  const wanted = String(profileDir || '');
  if (!wanted || !chromeProfilesIndex?.items) return null;
  return chromeProfilesIndex.items.find((item) => String(item.profile_dir || item.id || '') === wanted) || null;
}

function chromeProfileBadgeHtml(item) {
  const badges = [];
  if (item.is_consented_primary_account || item.is_primary) badges.push('<span class="chrome-profile-badge primary">primary</span>');
  if (item.user_name || item.email) badges.push('<span class="chrome-profile-badge">signed in</span>');
  if (item.bookmarks_exists) badges.push('<span class="chrome-profile-badge">bookmarks</span>');
  if (item.history_exists) badges.push('<span class="chrome-profile-badge">history</span>');
  const active = String(item.active_label || '').trim();
  if (active) badges.push(`<span class="chrome-profile-badge">${_escHtml(active)}</span>`);
  return badges.join('');
}

function microcosmWebsiteRowHtml() {
  const opening = chromeWebsiteOpenInFlight ? ' data-opening="true"' : '';
  return [
    `<button class="chrome-profile-row" type="button" data-window-action="website" title="Open the current Microcosm public site in the active Google Chrome window"${opening}>`,
    `<span class="chrome-profile-row-head">`,
    `<span class="chrome-profile-name">Website</span>`,
    `<span class="chrome-profile-email">current Microcosm public site</span>`,
    `<span class="chrome-profile-dir">cached static site</span>`,
    `</span>`,
    `<span class="chrome-profile-badges"><span class="chrome-profile-badge primary">Microcosm</span><span class="chrome-profile-badge">Chrome</span></span>`,
    `<span class="chrome-profile-path">sites/microcosm/index.html</span>`,
    `</button>`,
  ].join('');
}

function renderChromeProfilesDropdown() {
  if (!dropdownEls.chromeProfileRows) return;
  const websiteRow = microcosmWebsiteRowHtml();
  if (chromeProfilesIndex == null) {
    dropdownEls.chromeProfileRows.innerHTML = `${websiteRow}<div class="prompts-empty">loading Chrome profiles…</div>`;
    const posted = postNative('requestChromeProfiles');
    if (dropdownEls.chromeProfilesReceipt) {
      dropdownEls.chromeProfilesReceipt.textContent = posted ? 'loading normal Chrome profile store…' : 'native bridge unavailable';
    }
    if (!posted) {
      chromeProfilesIndex = { ok: false, error: 'native bridge unavailable', items: [] };
    }
    return;
  }
  if (!chromeProfilesIndex.ok) {
    const err = _escHtml(chromeProfilesIndex.error || 'unknown error');
    const stage = _escHtml(chromeProfilesIndex.stage || '');
    dropdownEls.chromeProfileRows.innerHTML = `${websiteRow}<div class="prompts-empty">Chrome profiles unavailable${stage ? ` (${stage})` : ''}: ${err}</div>`;
    return;
  }
  const items = chromeProfilesIndex.items || [];
  if (items.length === 0) {
    dropdownEls.chromeProfileRows.innerHTML = `${websiteRow}<div class="prompts-empty">no Chrome profiles found in the normal user data directory</div>`;
    return;
  }
  const html = items.map((item) => {
    const profileDir = _escHtml(item.profile_dir || item.id || '');
    const name = _escHtml(item.name || item.profile_name || item.profile_dir || 'Chrome profile');
    const email = _escHtml(item.user_name || item.email || item.gaia_name || '');
    const path = _escHtml(item.profile_path || '');
    const badges = chromeProfileBadgeHtml(item);
    const opening = chromeProfileOpenInFlight && chromeProfileOpenInFlight === (item.profile_dir || item.id) ? ' data-opening="true"' : '';
    const title = _escHtml(`Open ${item.name || item.profile_dir || 'Chrome profile'} in normal Google Chrome`);
    return [
      `<button class="chrome-profile-row" type="button" data-profile-dir="${profileDir}" title="${title}"${opening}>`,
      `<span class="chrome-profile-row-head">`,
      `<span class="chrome-profile-name">${name}</span>`,
      email ? `<span class="chrome-profile-email">${email}</span>` : '',
      `<span class="chrome-profile-dir">${profileDir}</span>`,
      `</span>`,
      badges ? `<span class="chrome-profile-badges">${badges}</span>` : '',
      path ? `<span class="chrome-profile-path">${path}</span>` : '',
      `</button>`,
    ].join('');
  }).join('');
  dropdownEls.chromeProfileRows.innerHTML = websiteRow + html;
}

function promptHotkeyStatusTitle(payload) {
  if (!payload || !payload.ok) {
    return `Hotkey status unavailable: ${payload?.error || payload?.stage || 'unknown'}`;
  }
  const mapCount = Number(payload.map_count || 0);
  const trust = payload.trusted === false ? 'Accessibility not trusted' : 'Accessibility trusted';
  const runtime = payload.enabled ? 'F1-F12 paste prompt-shelf prompts' : 'F1-F12 pass through normally';
  return `${runtime}. ${trust}. ${mapCount} prompt bindings.`;
}

function applyPromptShelfHotkeyStatus(payload) {
  const button = els.buttons.promptHotkeys;
  if (!button) return;
  promptHotkeysBusy = false;
  promptHotkeysEnabled = Boolean(payload?.enabled);
  button.disabled = false;
  button.setAttribute('aria-pressed', promptHotkeysEnabled ? 'true' : 'false');
  button.dataset.hotkeyState = payload?.ok === false
    ? 'failed'
    : promptHotkeysEnabled ? 'enabled' : 'disabled';
  button.textContent = promptHotkeysEnabled ? 'Hotkeys on' : 'Hotkeys off';
  button.title = promptHotkeyStatusTitle(payload);
  const stage = payload?.stage || '';
  if (stage === 'enabled' || stage === 'disabled' || stage === 'status') {
    els.status.textContent = promptHotkeysEnabled
      ? 'Prompt hotkeys active: F1-F12 paste prompt-shelf prompts.'
      : 'Prompt hotkeys off: F1-F12 use normal macOS/app behavior.';
  } else if (payload?.ok === false) {
    els.status.textContent = `Hotkey toggle failed: ${payload.error || payload.stage || 'unknown'}`;
  }
}

function requestPromptShelfHotkeyStatus() {
  const button = els.buttons.promptHotkeys;
  if (button) {
    button.dataset.hotkeyState = 'checking';
    button.textContent = 'Hotkeys…';
  }
  if (!postNative('requestPromptShelfHotkeyStatus')) {
    applyPromptShelfHotkeyStatus({ ok: false, stage: 'native_unavailable', error: 'native bridge unavailable' });
  }
}

function setPromptShelfHotkeysEnabled(enabled) {
  if (promptHotkeysBusy) return;
  promptHotkeysBusy = true;
  const button = els.buttons.promptHotkeys;
  if (button) {
    button.disabled = true;
    button.dataset.hotkeyState = enabled ? 'starting' : 'stopping';
    button.textContent = enabled ? 'Starting…' : 'Stopping…';
  }
  if (!postNative('setPromptShelfHotkeysEnabled', { enabled })) {
    promptHotkeysBusy = false;
    applyPromptShelfHotkeyStatus({ ok: false, stage: 'native_unavailable', error: 'native bridge unavailable' });
  }
}

function renderPromptsDropdown() {
  if (!dropdownEls.promptsRows) return;
  if (promptShelfIndex == null) {
    dropdownEls.promptsRows.innerHTML = '<div class="prompts-empty">loading prompts…</div>';
    postNative('requestPromptShelfIndex');
    return;
  }
  if (!promptShelfIndex.ok) {
    const err = _escHtml(promptShelfIndex.error || 'unknown error');
    const stage = _escHtml(promptShelfIndex.stage || '');
    dropdownEls.promptsRows.innerHTML = `<div class="prompts-empty">prompt shelf unavailable (${stage}): ${err}</div>`;
    return;
  }
  const items = promptShelfIndex.items || [];
  if (items.length === 0) {
    dropdownEls.promptsRows.innerHTML = '<div class="prompts-empty">no prompts in obsidian/prompt_shelf/items/</div>';
    return;
  }
  const html = items.map((item, index) => {
    const slot = _escHtml(item.slot || item.slug || '');
    const label = _escHtml(item.label || item.slot || '');
    const title = _escHtml(item.title || '');
    const status = _escHtml(item.status || '');
    const role = _escHtml(item.target_role || '');
    const when = _escHtml(item.when_to_use || '');
    const bytes = Number(item.char_count || 0);
    const uses = promptUsageCount(item);
    const frequencyTier = uses > 0 && index < 4 ? 'primary' : uses > 0 ? 'secondary' : 'rare';
    const sizeStr = bytes > 0 ? _formatKB(bytes) : '—';
    const statusBadge = status && status !== 'current' ? `<span class="prompts-status">${status}</span>` : '';
    const useBadge = uses > 0 ? `<span class="prompts-use">${uses}x</span>` : '';
    return [
      `<button class="prompts-row" type="button" data-prompt-slot="${slot}" data-frequency-tier="${frequencyTier}" title="${when}">`,
      `<span class="prompts-row-head">`,
      `<span class="prompts-label">${label}</span>`,
      `<span class="prompts-title">${title}</span>`,
      statusBadge,
      useBadge,
      `<span class="prompts-size">${sizeStr}</span>`,
      `</span>`,
      role ? `<span class="prompts-role">${role}</span>` : '',
      when ? `<span class="prompts-when">${when}</span>` : '',
      `</button>`,
    ].join('');
  }).join('');
  dropdownEls.promptsRows.innerHTML = html;
}

function renderClipboardDropdown() {
  const rows = savedCaptures || [];
  dropdownEls.clipboardRows.replaceChildren();
  if (!rows.length) {
    const e = document.createElement('div');
    e.className = 'dropdown-empty';
    e.textContent = 'No clipboard captures yet.';
    dropdownEls.clipboardRows.appendChild(e);
    [dropdownEls.clipboardCopyLatest, dropdownEls.clipboardCopyFull, dropdownEls.clipboardReveal].forEach(b => { if (b) b.disabled = true; });
    return;
  }
  rows.slice(0, 30).forEach((row, i) => {
    const div = document.createElement('div');
    div.className = 'dropdown-row';
    if (i === 0) div.setAttribute('aria-selected', 'true');
    const kind = (row.kind || 'capture').replace(/_/g, ' ');
    const bytes = row.contentBytes || row.bytes || row.chars || 0;
    const captured = row.timeLabel || row.capturedAt || '';
    const preview = (row.hudCaption || row.filename || '').slice(0, 80);
    div.innerHTML = `
      <span class="col-badge">CB</span>
      <span class="col-title">${_escHtml(kind)}</span>
      <span class="col-fresh ${kind.includes('agent') ? 'current' : ''}">${_escHtml(kind.toUpperCase().slice(0, 12))}</span>
      <span class="col-meta">${_escHtml(_formatKB(bytes))}</span>
      <span class="col-meta">${_escHtml(String(captured).slice(0, 8))}</span>
      <span class="col-meta">${_escHtml(String(row.events || ''))}</span>
      <span class="col-preview">${_escHtml(preview)}</span>
    `;
    dropdownEls.clipboardRows.appendChild(div);
  });
  [dropdownEls.clipboardCopyLatest, dropdownEls.clipboardCopyFull, dropdownEls.clipboardReveal].forEach(b => { if (b) b.disabled = false; });
}
dropdownEls.clipboardCopyLatest?.addEventListener('click', () => {
  dropdownEls.clipboardReceipt.textContent = 'Copying latest clip…';
  copyLatestClipboardClip();
});
dropdownEls.clipboardCopyFull?.addEventListener('click', () => {
  dropdownEls.clipboardReceipt.textContent = 'Copying full clip…';
  copyLatestClipboardClip();
});
dropdownEls.clipboardReveal?.addEventListener('click', () => {
  const row = savedCaptures[0];
  const path = row?.path || row?.exportPath || row?.storedPath || row?.clipStorePath || row?.rawPath || '';
  if (path && postNative('revealFile', { path })) {
    dropdownEls.clipboardReceipt.textContent = `Revealing ${path.split('/').pop()}`;
  } else {
    dropdownEls.clipboardReceipt.textContent = 'No revealable path.';
  }
});

function windowedMissionRows(rows) {
  const list = Array.isArray(rows) ? rows : [];
  const container = dropdownEls?.agentTraceRows;
  if (!container || list.length <= MISSION_WINDOWING_MIN_ROWS) {
    return {
      rows: list,
      start: 0,
      end: list.length,
      topSpacer: 0,
      bottomSpacer: 0,
      windowed: false,
      scrollProfile: missionRowsScrollProfile(),
    };
  }
  const scrollProfile = missionRowsScrollProfile();
  const viewport = Math.max(container.clientHeight || 360, MISSION_ROW_HEIGHT_PX * 6);
  const start = missionWindowStartForScrollTop(container.scrollTop || 0, scrollProfile, list);
  const count = Math.ceil(viewport / MISSION_ROW_HEIGHT_PX)
    + scrollProfile.overscanRows * 2
    + scrollProfile.windowStepRows;
  const end = Math.min(list.length, start + count);
  return {
    rows: list.slice(start, end),
    start,
    end,
    topSpacer: missionRenderItemsHeight(list, 0, start),
    bottomSpacer: missionRenderItemsHeight(list, end, list.length),
    windowed: true,
    scrollProfile,
  };
}

function missionRenderItemHeight(item) {
  return item?.kind === 'lane' ? MISSION_LANE_ROW_HEIGHT_PX : MISSION_ROW_HEIGHT_PX;
}

function missionRenderItemsHeightPrefix(items) {
  const list = Array.isArray(items) ? items : [];
  let prefix = missionRenderHeightPrefixCache.get(list);
  if (!prefix) {
    prefix = new Array(list.length + 1);
    prefix[0] = 0;
    for (let i = 0; i < list.length; i += 1) {
      prefix[i + 1] = prefix[i] + missionRenderItemHeight(list[i]);
    }
    missionRenderHeightPrefixCache.set(list, prefix);
  }
  return prefix;
}

function missionRenderItemsHeight(items, start = 0, end = items?.length || 0) {
  const list = Array.isArray(items) ? items : [];
  const first = Math.max(0, Math.min(start, list.length));
  const last = Math.max(first, Math.min(end, list.length));
  if (first === last) return 0;
  const prefix = missionRenderItemsHeightPrefix(list);
  return (prefix[last] || 0) - (prefix[first] || 0);
}

function missionItemIndexForScrollTop(items, scrollTop = 0) {
  const list = Array.isArray(items) ? items : [];
  if (!list.length) return Math.max(0, Math.floor((Number(scrollTop) || 0) / MISSION_ROW_HEIGHT_PX));
  const target = Math.max(0, Number(scrollTop) || 0);
  const prefix = missionRenderItemsHeightPrefix(list);
  let lo = 0;
  let hi = list.length;
  while (lo < hi) {
    const mid = Math.floor((lo + hi) / 2);
    if ((prefix[mid + 1] || 0) <= target) lo = mid + 1;
    else hi = mid;
  }
  return Math.max(0, Math.min(lo, list.length - 1));
}

function missionWindowStartForScrollTop(scrollTop = 0, scrollProfile = missionRowsScrollProfile(), items = null) {
  const overscanRows = Number(scrollProfile?.overscanRows) || MISSION_RENDER_OVERSCAN_ROWS;
  const stepRows = Number(scrollProfile?.windowStepRows) || MISSION_RENDER_WINDOW_STEP_ROWS;
  const scrollIndex = Array.isArray(items)
    ? missionItemIndexForScrollTop(items, scrollTop)
    : Math.floor((Number(scrollTop) || 0) / MISSION_ROW_HEIGHT_PX);
  const rawStart = Math.max(0, scrollIndex - overscanRows);
  return Math.floor(rawStart / stepRows) * stepRows;
}

// True only when scrolling has moved far enough to bring a new slice of rows
// into the virtualized window (same start formula as windowedMissionRows). Lets
// the scroll handler skip the expensive full re-render while scrolling within
// the already-rendered overscan band.
function missionScrollWindowChanged() {
  const container = dropdownEls?.agentTraceRows;
  if (!container) return false;
  const scrollProfile = missionRowsScrollProfile();
  const start = missionWindowStartForScrollTop(container.scrollTop || 0, scrollProfile, missionRowsRenderCache?.renderItems);
  return start !== (lastMissionRowsRenderStats.start || 0)
    || scrollProfile.profile !== (lastMissionRowsRenderStats.scroll_profile || 'normal');
}

const MISSION_SCROLL_RESET_REASONS = new Set([
  'open_dropdown',
  'search_input',
  'api_search',
  'sort_change',
  'api_sort',
  'toggle_inactive_missions',
]);

function shouldPreserveMissionRowsScroll(reason = 'render', scrollTop = 0) {
  if (!scrollTop) return false;
  const key = String(reason || 'render');
  if (MISSION_SCROLL_RESET_REASONS.has(key)) return false;
  return !key.includes('search') && !key.includes('sort');
}

function restoreMissionRowsScrollTop(container, scrollTop) {
  if (!container || !scrollTop) return;
  const maxScrollTop = Math.max(0, (container.scrollHeight || 0) - (container.clientHeight || 0));
  const target = Math.max(0, Math.min(scrollTop, maxScrollTop));
  if (Math.abs((container.scrollTop || 0) - target) > 1) {
    container.scrollTop = target;
  }
}

function isMissionRowsOnlyRender(reason = 'render') {
  return ['mission_row_scroll', 'mission_rows_resize'].includes(String(reason || ''));
}

function missionRowsRenderCacheSignature() {
  return [
    dropdownSearch || '',
    dropdownSortMode || '',
    showInactiveMissions ? 'inactive' : 'active',
    selectedTraceSourceWindow(),
    String(expandedSubagentParentVersion),
  ].join('\u0001');
}

function cachedMissionRowsRenderPayload(reason = 'render') {
  if (!isMissionRowsOnlyRender(reason)) return null;
  if (!missionRowsRenderCache?.renderItems?.length) return null;
  if (missionRowsRenderCache.signature !== missionRowsRenderCacheSignature()) return null;
  return missionRowsRenderCache;
}

function rememberMissionRowsRenderPayload(payload) {
  missionRowsRenderCache = payload?.renderItems?.length
    ? { ...payload, signature: missionRowsRenderCacheSignature() }
    : null;
}

function missionRowsAppendTarget() {
  return missionRowsRenderFragment || dropdownEls?.agentTraceRows || null;
}

function appendMissionRowsNode(node) {
  const target = missionRowsAppendTarget();
  if (target && node) target.appendChild(node);
}

function appendMissionRowSpacer(heightPx) {
  if (!heightPx) return;
  const spacer = document.createElement('div');
  spacer.className = 'dropdown-row-spacer';
  spacer.style.height = `${heightPx}px`;
  appendMissionRowsNode(spacer);
}

function appendMissionRowError(row, error) {
  if (!missionRowsAppendTarget()) return;
  const message = rememberUncaughtWorkbenchError('row_render', error);
  const div = document.createElement('div');
  div.className = 'dropdown-row row-error';
  div.dataset.activity = 'error';
  div.dataset.novelty = 'known';
  div.dataset.copy = 'none';
  div.innerHTML = `
    <span class="col-badge">${_escHtml(providerLabel(row?.provider))}</span>
    <span class="col-title"><span class="life-glyph" aria-hidden="true">!</span><span class="title-text">${_escHtml(row?.title || row?.short_label || 'Unreadable mission row')}</span></span>
    <span class="col-fresh capture-failed">ROW ERROR</span>
    <span class="col-meta col-turn">—</span>
    <span class="col-meta col-source">${_escHtml(message.slice(0, 32))}</span>
  `;
  div.title = `Row render failed: ${message}. Refresh or copy latest response bundle if the mission can still be selected.`;
  appendMissionRowsNode(div);
}

function missionListPaneEl() {
  return dropdownEls?.agentTraceRows?.closest?.('.mission-list-pane') || null;
}

function missionStatusText(row, renderStart = Date.now()) {
  const displayTurn = activityDisplayTurn(row);
  const fresh = (row.artifact_freshness || {}).state || 'unknown';
  const reason = (row.artifact_freshness || {}).reason || '';
  const flabel = _freshLabel(
    fresh,
    reason,
    displayTurn.turn_index != null,
    sourceFreshnessState(row),
    rowHasActiveTrace(row),
  );
  const pill = missionWorkflowPill(row, missionViewStateForRow(row, renderStart), flabel);
  return String(pill?.text || '').toUpperCase();
}

function updateMissionPaneHeader(rows, renderStart = Date.now()) {
  const list = Array.isArray(rows) ? rows : [];
  const pane = missionListPaneEl();
  if (pane) pane.dataset.showInactive = showInactiveMissions ? 'true' : 'false';
  updateMissionSearchProvenance(list);
  if (dropdownEls?.agentTraceMissionCounts) {
    const counts = { running: 0, waiting: 0, finished: 0, other: 0 };
    const laneCounts = {};
    list.forEach((row) => {
      const text = missionStatusText(row, renderStart);
      if (text.includes('RUNNING')) counts.running += 1;
      else if (text.includes('WAITING') || text.includes('WAIT')) counts.waiting += 1;
      else if (text.includes('FINISHED')) counts.finished += 1;
      else counts.other += 1;
      const lane = missionAttentionForRow(row, renderStart).lane;
      laneCounts[lane] = (laneCounts[lane] || 0) + 1;
    });
    const next = list.map((row) => ({ row, attn: missionAttentionForRow(row, renderStart) }))
      .filter((item) => !['retired', 'older_finished_copied'].includes(item.attn.lane))
      .sort((a, b) => (b.attn.attention_score || 0) - (a.attn.attention_score || 0))[0];
    const nextText = next
      ? `next ${missionAttentionLaneLabel(next.attn.lane)}: ${missionDisplayTitle(next.row, activityDisplayTurn(next.row)).slice(0, 44)}`
      : '';
    const hidden = hiddenInactiveCount();
    const refresh = missionIndexRefreshPending
      ? `refreshing ${compactAgeLabel(missionIndexRefreshStartedAt ? new Date(missionIndexRefreshStartedAt).toISOString() : '')}`
      : missionIndex?.generated_at
        ? `refreshed ${compactAgeLabel(missionIndex.generated_at)}`
        : '';
    const goalSummary = missionGoalSummaryText();
    dropdownEls.agentTraceMissionCounts.textContent = [
      `${list.length} shown`,
      goalSummary,
      `running ${counts.running}`,
      `waiting ${counts.waiting}`,
      `finished ${counts.finished}`,
      laneCounts.needs_review_now ? `review ${laneCounts.needs_review_now}` : '',
      laneCounts.ready_to_copy ? `copy ${laneCounts.ready_to_copy}` : '',
      laneCounts.rogue_active ? `risky ${laneCounts.rogue_active}` : '',
      nextText,
      hidden ? `${hidden} inactive hidden` : showInactiveMissions ? 'inactive shown' : '',
      refresh,
    ].filter(Boolean).join(' · ');
  }
  if (dropdownEls?.missionPaneToggleInactive) {
    const hidden = hiddenInactiveCount();
    const inactiveTotal = inactiveMissionRows().length;
    dropdownEls.missionPaneToggleInactive.hidden = !inactiveTotal;
    dropdownEls.missionPaneToggleInactive.textContent = showInactiveMissions
      ? `Hide inactive (${inactiveTotal})`
      : `Show inactive / old missions (${hidden || inactiveTotal})`;
    dropdownEls.missionPaneToggleInactive.setAttribute('aria-pressed', showInactiveMissions ? 'true' : 'false');
  }
  if (!dropdownEls?.agentTraceSelectedBrief) return;
  const sel = findMissionByKey(selectedMissionKey);
  if (!sel) {
    dropdownEls.agentTraceSelectedBrief.textContent = 'Select a mission';
    return;
  }
  const displayTurn = activityDisplayTurn(sel);
  const turn = displayTurn.turn_index != null ? `${rowHasActiveTrace(sel) ? 'active' : 'turn'} #${displayTurn.turn_index}` : 'no turn';
  const scope = traceCapsuleCopySize(sel, selectedTraceSourceWindow(), displayTurn);
  const stateModel = missionStateModel(sel, selectedTraceSourceWindow(), renderStart);
  dropdownEls.agentTraceSelectedBrief.textContent = [
    providerShortBadge(sel.provider),
    missionDisplayTitle(sel, displayTurn),
    stateModel.mission_attention?.lane_label || '',
    `runtime ${stateModel.runtime_state.replace(/_/g, ' ')}`,
    stateModel.goal_state !== 'none' ? `goal ${stateModel.goal_state.replace(/_/g, ' ')}` : '',
    `artifact ${stateModel.artifact_state.replace(/_/g, ' ')}`,
    `diff ${stateModel.diff_state.replace(/_/g, ' ')}`,
    turn,
    scope?.label || '',
  ].filter(Boolean).join(' · ');
}

function missionIndexEnvelopeProvenanceText() {
  const data = lastMissionIndexEnvelope || {};
  const parts = [];
  const indexMtime = _numberOrNull(missionIndex?._source_index_mtime_ms);
  if (indexMtime) parts.push(`index ${compactAgeLabel(new Date(indexMtime).toISOString())}`);
  else if (missionIndex?.generated_at) parts.push(`index ${compactAgeLabel(missionIndex.generated_at)}`);
  const titleLatest = data.title_authority?.latest_mtime || '';
  if (data.title_authority_status) parts.push(`titles ${String(data.title_authority_status).replace(/_/g, ' ')}`);
  else if (data.title_authority_stale) parts.push('titles newer than index');
  else if (titleLatest) parts.push(`titles ${compactAgeLabel(titleLatest)}`);
  if (data.goal_authority_stale) parts.push('goals newer than index');
  const sourceActivity = data.source_activity || {};
  const changed = Number(sourceActivity.changed_count || 0);
  if (changed > 0) {
    const quiet = Number(sourceActivity.quiet_changed_count || 0);
    parts.push(`source ${quiet}/${changed} quiet changes`);
  }
  return parts.filter(Boolean).join(' · ');
}

function updateMissionSearchProvenance(rows = []) {
  const el = dropdownEls?.agentTraceSearchProvenance;
  if (!el) return;
  const query = String(dropdownSearch || '').trim();
  const provenance = missionIndexEnvelopeProvenanceText();
  if (!query) {
    el.textContent = provenance || 'index loading';
    el.dataset.searchState = provenance ? 'index' : 'empty';
    return;
  }
  const list = Array.isArray(rows) ? rows : [];
  const top = list[0] || null;
  if (!top) {
    el.textContent = [`"${query}"`, '0 matches', provenance].filter(Boolean).join(' · ');
    el.dataset.searchState = 'empty';
    return;
  }
  const score = missionSearchScore(top, query);
  const source = missionSearchMatchSource(top, query, score);
  const title = missionDisplayTitle(top, activityDisplayTurn(top)) || shortSessionId(top?.session_id);
  const exact = score >= 100_000_000 ? 'exact' : 'matched';
  el.textContent = [
    `"${query}"`,
    `${list.length} match${list.length === 1 ? '' : 'es'}`,
    `${exact} ${source}: ${title}`,
    provenance,
  ].filter(Boolean).join(' · ');
  el.dataset.searchState = exact;
}

function missionTraceCellLabel(copySize) {
  const raw = String(copySize?.label || '').trim();
  if (!raw) return '—';
  const kb = raw.match(/(~?\d+(?:\.\d+)?\s*KB)\b/i);
  if (kb) return kb[1].replace(/\s+/g, ' ');
  if (/after prepare/i.test(raw)) return 'prep';
  return raw
    .replace(/^copy\s+/i, '')
    .replace(/^last\s+/i, '')
    .replace(/^trace capsule\s+/i, '')
    .replace(/^thread compact\s+/i, '')
    .replace(/\s+/g, ' ')
    .slice(0, 18) || '—';
}

function missionAgeFields(row, displayTurn, activeTrace) {
  const finishedAt = displayTurn?.completed_at || row?.latest_completed_turn?.completed_at || null;
  const activeAt = displayTurn?.started_at || row?.active_turn?.started_at || null;
  const copiedAt = row?.latest_clip?.captured_at || null;
  const sourceAt = row?.source_freshness?.source_last_event_at || row?.source_last_event_at || row?.mtime_utc || null;
  const staleSource = !activeTrace && (isSourceIndexStale(row) || rowHasSoftStaleTraceSummary(row));
  let source = activeTrace
    ? (activeAt || row?.last_activity_at || row?.updated_at || row?.generated_at)
    : (finishedAt || row?.last_activity_at || row?.updated_at || row?.generated_at);
  if (staleSource && sourceAt) source = sourceAt;
  const age = compactAgeLabel(source);
  // v7: distinct, labeled timestamps so a single "1h ago" can no longer hide
  // whether it measures finish, copy, or source-file time (operator trust gap).
  const parts = [];
  if (activeTrace && activeAt) parts.push(`active since ${compactAgeLabel(activeAt)} (${exactTimeLabel(activeAt)})`);
  if (finishedAt) parts.push(`finished ${compactAgeLabel(finishedAt)} (${exactTimeLabel(finishedAt)})`);
  if (copiedAt) parts.push(`copied ${compactAgeLabel(copiedAt)} (${exactTimeLabel(copiedAt)})`);
  if (sourceAt) parts.push(`source updated ${compactAgeLabel(sourceAt)} (${exactTimeLabel(sourceAt)})`);
  if (staleSource && sourceAt) parts.push('showing source update because trace index is stale');
  return {
    text: age,
    title: parts.length
      ? parts.join(' · ')
      : (activeTrace ? `active since ${exactTimeLabel(source)}` : `last activity ${exactTimeLabel(source)}`),
    kind: activeTrace ? 'active' : (staleSource ? 'source' : 'finished'),
  };
}

function missionQueuePreview(row, displayTurn, preview, scope, flabel, activeTrace) {
  const turnText = displayTurn?.turn_index != null
    ? `${activeTrace ? 'active' : 'turn'} #${displayTurn.turn_index}`
    : 'no turn';
  const bits = [];
  if (preview) bits.push(preview);
  bits.push(turnText);
  if (scope?.large) bits.push('large trace');
  if (flabel?.text && !/(current|ready|source live)/i.test(flabel.text)) bits.push(String(flabel.text).toLowerCase());
  const subagents = missionSubagentOperatorText(row);
  if (subagents) bits.push(subagents);
  return bits.filter(Boolean).join(' · ');
}

function renderAgentTraceDropdown(reason = 'render') {
  // v7: memo window — missionAttentionForRow caches per row for this render only,
  // collapsing the old sort-comparator + forEach double full-pipeline compute.
  beginMissionAttentionMemo();
  try {
    return renderAgentTraceDropdownBody(reason);
  } finally {
    endMissionAttentionMemo();
  }
}

function renderAgentTraceDropdownBody(reason = 'render') {
  const rowsContainer = dropdownEls?.agentTraceRows || null;
  const previousScrollTop = rowsContainer ? (rowsContainer.scrollTop || 0) : 0;
  const preserveScroll = shouldPreserveMissionRowsScroll(reason, previousScrollTop);
  const rowsOnlyRender = isMissionRowsOnlyRender(reason);
  const cachedRenderPayload = cachedMissionRowsRenderPayload(reason);
  const renderStart = Date.now();
  let allRows = cachedRenderPayload?.allRows || [];
  let rows = cachedRenderPayload?.rows || [];
  let renderItems = cachedRenderPayload?.renderItems || [];
  let selectedSourceWindow = cachedRenderPayload?.selectedSourceWindow || selectedTraceSourceWindow();
  if (!cachedRenderPayload) {
    allRows = visibleMissionRows();
    rows = sortedMissionRows(allRows);
    if (dropdownSearch) {
      const q = dropdownSearch.toLowerCase();
      // v7 relevance ranking: ordinal-first, then score desc, then newest-first
      // (duplicate ordinals group newest-on-top), then ordinal desc.
      const scored = [];
      for (const r of rows) {
        const s = missionSearchScore(r, q);
        if (s > 0) scored.push([r, s]);
      }
      scored.sort((a, b) => (b[1] - a[1])
        || (_missionSortTime(b[0]) - _missionSortTime(a[0]))
        || ((b[0].mission_ordinal_key || 0) - (a[0].mission_ordinal_key || 0)));
      rows = scored.map((entry) => entry[0]);
      ensureSelectedMissionInRows(rows);
    } else {
      ensureSelectedMission(rows);
    }
    if (!rowsOnlyRender) updateMissionPaneHeader(rows, renderStart);
    if (!rows.length) {
      rememberMissionRowsRenderPayload(null);
      const e = document.createElement('div');
      e.className = 'dropdown-empty';
      e.textContent = missionIndex
        ? (dropdownSearch ? 'No matching missions.' : 'No active missions.')
        : 'Mission index loading…';
      dropdownEls.agentTraceRows.replaceChildren(e);
      if (rowsOnlyRender) return;
      [
        dropdownEls.missionCaptureCopy,
        dropdownEls.missionCopyCloseout,
        dropdownEls.missionDownloadDenoised,
        dropdownEls.missionPaneCopyCapsule,
        dropdownEls.missionPaneCopyCloseout,
        dropdownEls.missionPaneSaveReveal,
        dropdownEls.missionPanePin,
        dropdownEls.missionPaneSnooze,
        dropdownEls.missionPaneReviewed,
      ].forEach((button) => { if (button) button.disabled = true; });
      renderMissionScopeContract(null, selectedTraceSourceWindow());
      return;
    }
    ensureSelectedMission(allRows);
    selectedSourceWindow = selectedTraceSourceWindow();
    pruneMissionViewState(renderStart);
    pruneExpandedSubagentParents(allRows);
    renderItems = missionRenderRows(rows, {
      expandedParentKeys: expandedSubagentParentKeys,
      forceExpandSubagents: Boolean(dropdownSearch),
      includeAttentionLanes: dropdownSortMode === 'review_first' && !dropdownSearch,
      renderStart,
    });
    rememberMissionRowsRenderPayload({ allRows, rows, renderItems, selectedSourceWindow });
  }
  const windowed = windowedMissionRows(renderItems);
  const renderFragment = document.createDocumentFragment();
  const previousMissionRowsRenderFragment = missionRowsRenderFragment;
  missionRowsRenderFragment = renderFragment;
  try {
    appendMissionRowSpacer(windowed.topSpacer);
    windowed.rows.forEach(item => {
      const row = item?.row || item;
      try {
        if (item?.kind === 'lane') {
          const div = document.createElement('div');
          div.className = 'mission-lane-row';
          div.dataset.attentionLane = item.lane || '';
          div.textContent = item.label || missionAttentionLaneLabel(item.lane);
          appendMissionRowsNode(div);
          return;
        }
        const k = missionKey(row);
        if (item?.kind === 'subagent') {
          const dep = item.deployment || {};
          const label = missionSubagentLabel(dep);
          const turnIndex = dep.turn_index != null ? `#${dep.turn_index}` : '—';
          const status = missionSubagentStatusLabel(dep);
          const relKind = missionSubagentRelationshipKind(dep);
          const childMissionKey = missionSubagentTargetMissionKey(dep);
          const typeModel = [dep.subagent_type || dep.attribution_agent || '', dep.model || dep.child_trace?.model || ''].filter(Boolean).join(' · ') || dep.tool_name || 'Agent';
          const traceStats = missionSubagentTraceStats(dep);
          const preview = String(traceStats || dep.prompt_preview || dep.description || '').slice(0, 110);
          const div = document.createElement('div');
          div.className = `dropdown-row subagent-row ${dep.linked_child_trace ? 'linked-subagent-row' : ''}`;
          div.dataset.missionKey = k;
          div.dataset.subagentKey = item.key || dep.tool_call_id || '';
          div.dataset.provider = missionProviderKey(row.provider);
          div.dataset.activity = 'subagent';
          div.dataset.novelty = 'known';
          div.dataset.copy = 'none';
          div.dataset.relationship = relKind;
          if (childMissionKey) div.dataset.childMissionKey = childMissionKey;
          if (k === selectedMissionKey) div.dataset.parentSelected = 'true';
          div.innerHTML = `
            <span class="col-fresh subagent ${dep.linked_child_trace ? 'linked' : ''}">${_escHtml(status || 'SUBAGENT')}</span>
            <span class="col-title">
              <span class="mission-row-titleline"><span class="life-glyph" aria-hidden="true">&gt;</span><span class="title-text">${_escHtml(label)}</span></span>
              <span class="mission-row-preview">${_escHtml([typeModel, preview || `tool ${dep.tool_call_id || dep.tool_index || ''}`, `parent ${turnIndex}`].filter(Boolean).join(' · '))}</span>
            </span>
            <span class="col-meta col-trace" title="${_escHtml(childMissionKey ? 'selectable linked child trace' : (dep.linked_child_trace ? 'linked child trace' : 'deployment event only'))}">${_escHtml(childMissionKey ? 'open' : (dep.linked_child_trace ? 'linked' : 'event'))}</span>
            <span class="col-meta col-age" title="${_escHtml(exactTimeLabel(dep.completed_at || dep.started_at))}">${_escHtml(compactAgeLabel(dep.completed_at || dep.started_at))}</span>
          `;
          div.title = `${label} · ${status.toLowerCase()} · child of ${missionDisplayTitle(row, traceDisplayTurn(row)) || shortSessionId(row.session_id)}${childMissionKey ? ' · click opens child trace capsule row' : ''} · ${typeModel}${traceStats ? ' · ' + traceStats : ''}`;
          div.setAttribute('aria-label', `Sub-agent ${label} ${status.toLowerCase()} under ${missionDisplayTitle(row, traceDisplayTurn(row)) || shortSessionId(row.session_id)}${childMissionKey ? ', opens child trace row' : ''}`);
          appendMissionRowsNode(div);
          return;
        }
        const fresh = (row.artifact_freshness || {}).state || 'unknown';
        const lct = traceDisplayTurn(row);
        const displayTurn = activityDisplayTurn(row);
        const activeTrace = rowHasActiveTrace(row);
        const primaryVariant = tracePrimaryVariantForSource(selectedSourceWindow);
        const capsuleArtifact = variantArtifact(row, primaryVariant, selectedSourceWindow);
        const capsuleCurrentness = variantArtifactCurrentness(row, capsuleArtifact, primaryVariant, selectedSourceWindow);
        const sourceBytes = row.size_bytes || 0;
        const sourceStr = sourceBytes ? _formatKB(sourceBytes) : '—';
        const preview = missionPromptPreview(row, displayTurn).slice(0, 90);
        const view = missionViewStateForRow(row, renderStart);
        const attention = missionAttentionForRow(row, renderStart, selectedSourceWindow);
        const glyph = missionViewStateGlyph(view);
        const scope = traceScopeMetrics(row, selectedSourceWindow, displayTurn);
        const copySize = traceCapsuleCopySize(row, selectedSourceWindow, displayTurn);
        const subagentCount = missionSubagentCount(row);
        const subagentLinkedCount = missionSubagentLinkedCount(row);
        const subagentsExpanded = missionShouldExpandSubagents(row, {
          expandedParentKeys: expandedSubagentParentKeys,
          forceExpandSubagents: Boolean(dropdownSearch),
        });
        const subagentChip = subagentCount
          ? `<button class="subagent-count-chip" type="button" data-subagent-toggle="${_escHtml(k)}" aria-expanded="${subagentsExpanded ? 'true' : 'false'}" title="${_escHtml(`${subagentsExpanded ? 'Collapse' : 'Expand'} ${missionSubagentOperatorText(row)}${subagentsExpanded ? '' : ' · collapsed under this thread'}`)}"><span class="subagent-disclosure-glyph" aria-hidden="true">${subagentsExpanded ? '-' : '+'}</span>${_escHtml(`${subagentCount} agent${subagentCount === 1 ? '' : 's'}${subagentLinkedCount ? ` · ${subagentLinkedCount} linked` : ''}`)}</button>`
          : '';
        const goalChip = missionGoalChip(row);
        const div = document.createElement('div');
        div.className = 'dropdown-row';
        div.dataset.missionKey = k;
        div.dataset.provider = missionProviderKey(row.provider);
        // Three orthogonal layers. aria-selected is reserved for actual selection
        // state (WAI-ARIA tabs pattern); lifecycle uses data-* + visible glyph +
        // title text so non-color signal is always present.
        div.dataset.activity = view.activity;
        div.dataset.novelty = view.novelty;
        div.dataset.copy = view.copy;
        div.dataset.attentionLane = attention.lane;
        div.dataset.attentionState = attention.attention_state;
        div.dataset.riskState = attention.risk_state;
        div.dataset.waitingKind = attention.waiting_kind;
        div.dataset.goalStatus = missionGoalStatus(row);
        div.dataset.goalAction = missionGoalFleetAction(row);
        if (subagentCount) div.dataset.subagents = subagentsExpanded ? 'expanded' : 'collapsed';
        if (k === selectedMissionKey) div.setAttribute('aria-selected', 'true');
        const reason = (row.artifact_freshness || {}).reason || '';
        const flabel = _freshLabel(fresh, reason, displayTurn.turn_index != null, sourceFreshnessState(row), activeTrace);
        const statusPill = missionWorkflowPill(row, view, flabel);
        const copySummary = view.copy !== 'none'
          ? missionCopySummary(view.copyEntry, renderStart, { includeScope: true })
          : '';
        const previewText = copySummary
          ? `${view.copy === 'just_copied' ? 'Copied' : 'Copy'} · ${copySummary}`
          : (preview || `session ${shortSessionId(row.session_id)} · raw ${sourceStr}`);
        const glyphTitle = glyph.title ? ` · ${glyph.title}` : '';
        const traceText = missionTraceCellLabel(copySize);
        const age = missionAgeFields(row, displayTurn, activeTrace);
        const attentionCue = attention.attention_reasons?.[0] || '';
        const searchCue = dropdownSearch ? 'search hit · select row, copy capsule/full thread, or reveal source' : '';
        // Lead the preview with the actual prompt/content — the per-row signal the
        // operator scans for. The attention cue (often the same "copy readiness
        // amber: …" boilerplate on every row) and search hint follow, so they
        // truncate off instead of burying the prompt. State is already on the pill.
        const queuePreview = missionQueuePreview(row, displayTurn, [previewText, attentionCue, searchCue].filter(Boolean).join(' · '), scope, flabel, activeTrace);
        div.innerHTML = `
          <span class="col-fresh ${statusPill.cls}" title="${_escHtml(statusPill.title)}">${_escHtml(statusPill.text)}</span>
          <span class="col-title">
            <span class="mission-row-titleline"><span class="life-glyph" aria-hidden="true" title="${_escHtml(glyph.title)}">${_escHtml(glyph.glyph)}</span><span class="title-text">${_escHtml(missionDisplayTitle(row, displayTurn))}</span>${goalChip}${subagentChip}</span>
            <span class="mission-row-preview">${_escHtml(queuePreview)}</span>
          </span>
          <span class="col-meta col-trace" title="${_escHtml(copySize.label)}${scope.large ? ' · large/slow' : ''}">${_escHtml(traceText)}</span>
          <span class="col-meta col-age" data-age-kind="${_escHtml(age.kind || '')}" title="${_escHtml(age.title)}">${_escHtml(age.text)}</span>
        `;
        const goalAction = missionGoalFleetAction(row);
        const goalActionAria = goalAction ? ` · goal action ${goalAction.replace(/_/g, ' ')}` : '';
        const goalAria = missionGoal(row) ? ` · ${missionGoalOperatorText(row)}${goalActionAria}` : '';
        div.setAttribute('aria-label', `${providerLabel(row.provider)} ${missionDisplayTitle(row, displayTurn)} · ${attention.lane_label} · risk ${attention.risk_state} · session ${shortSessionId(row.session_id)} · ${statusPill.text.toLowerCase()}${goalAria}${view.novelty === 'newly_seen' ? ' · newly seen' : ''}${view.copy !== 'none' ? ' · ' + view.copy.replace(/_/g, ' ') : ''}${glyphTitle}`);
        appendMissionRowsNode(div);
      } catch (error) {
        appendMissionRowError(row, error);
      }
    });
    appendMissionRowSpacer(windowed.bottomSpacer);
  } finally {
    missionRowsRenderFragment = previousMissionRowsRenderFragment;
  }
  dropdownEls.agentTraceRows.replaceChildren(renderFragment);
  if (preserveScroll) restoreMissionRowsScrollTop(rowsContainer, previousScrollTop);
  updateMissionRowsScrollAffordance();
  const scrollProfile = windowed.scrollProfile || missionRowsScrollProfile();
  lastMissionRowsScrollProfileStats = {
    profile: scrollProfile.profile || 'normal',
    overscan_rows: scrollProfile.overscanRows || MISSION_RENDER_OVERSCAN_ROWS,
    window_step_rows: scrollProfile.windowStepRows || MISSION_RENDER_WINDOW_STEP_ROWS,
    fast_scrolling: Boolean(scrollProfile.fastScrolling),
  };
  lastMissionRowsRenderStats = {
    total: renderItems.length,
    rendered: windowed.rows.length,
    start: windowed.start,
    end: windowed.end,
    duration_ms: Date.now() - renderStart,
    windowed: windowed.windowed,
    cached_payload: Boolean(cachedRenderPayload),
    scroll_profile: lastMissionRowsScrollProfileStats.profile,
    overscan_rows: lastMissionRowsScrollProfileStats.overscan_rows,
    window_step_rows: lastMissionRowsScrollProfileStats.window_step_rows,
    fast_scrolling: lastMissionRowsScrollProfileStats.fast_scrolling,
  };
  // Schedule a lifecycle tick so transitions across the band boundaries
  // (recent → warm → idle, just_copied → pending_after_copy → cleared,
  // newly_seen → known) paint without operator interaction.
  scheduleMissionLifecycleTick();
  scheduleMissionFinishedAutoRefresh();
  scheduleMissionTitleAuthoritySync();
  if (rowsOnlyRender) return;
  // Detail line + action button state (v3 vocabulary + KB sizes per variant).
  const sel = findMissionByKey(selectedMissionKey);
  if (sel) {
    const lct = traceDisplayTurn(sel);
    const displayTurn = activityDisplayTurn(sel);
    const activeTrace = rowHasActiveTrace(sel);
    const fresh = (sel.artifact_freshness || {}).state || 'unknown';
    const reason = (sel.artifact_freshness || {}).reason || '';
    const flabel = _freshLabel(fresh, reason, displayTurn.turn_index != null, sourceFreshnessState(sel), activeTrace);
    const primaryVariant = tracePrimaryVariantForSource(selectedSourceWindow);
    const primaryVariantLabel = tracePrimaryVariantLabel(primaryVariant, selectedSourceWindow);
    const capsuleArtifact = variantArtifact(sel, primaryVariant, selectedSourceWindow);
    const capsuleCurrentness = variantArtifactCurrentness(sel, capsuleArtifact, primaryVariant, selectedSourceWindow);
    const capsuleBytes = capsuleArtifact?.bytes || 0;
    const capsuleKB = capsuleBytes ? _formatKB(capsuleBytes) : '—';
    const copySize = traceCapsuleCopySize(sel, selectedSourceWindow, displayTurn);
    const stateModel = missionStateModel(sel, selectedSourceWindow);
    const copyReadiness = stateModel.copy_readiness || {};
    const sourceLatestFallback = traceCopyCanUseSourceLatestFallback(sel, selectedSourceWindow, activeTrace, stateModel);
    const visibleIndexRefresh = traceCopyRequiresVisibleIndexRefresh(sel, selectedSourceWindow, activeTrace, stateModel);
    dropdownEls.agentTraceDetail.textContent = selectedMissionOperatorChip(sel, selectedSourceWindow);
    renderMissionScopeContract(sel, selectedSourceWindow);
    // v7 copy-first action model: Copy buttons ALWAYS enabled when the
    // mission has a completed turn. The underlying copySelectedMission
    // Artifact() bridge already runs ensure-then-copy semantics
    // (skip_capture_if_current=true). Buttons should not be gated on
    // pre-existing artifact_refs — that was the v6 defect.
    const hasTraceTurn = displayTurn.turn_index != null;
    const copyActionText = !hasTraceTurn
      ? 'No Trace Turn'
      : copyReadiness.state === 'red'
        ? (primaryVariant === 'closeout_report' ? 'Blocked Compact' : 'Blocked Capsule')
      : sourceLatestFallback
        ? (primaryVariant === 'closeout_report' ? 'Copy Source Closeout' : 'Copy Source Latest')
      : visibleIndexRefresh
        ? 'Refresh Trace List'
      : capsuleCurrentness.ready
        ? (primaryVariant === 'closeout_report' ? 'Copy Thread Compact' : 'Copy Trace Capsule')
        : (capsuleCurrentness?.source_freshness?.action === 'block_copy')
          ? (primaryVariant === 'closeout_report' ? 'Blocked Compact' : 'Blocked Capsule')
        : (capsuleArtifact?.path || fresh === 'stale' || capsuleCurrentness?.source_freshness?.action === 'refresh_before_copy')
          ? (primaryVariant === 'closeout_report' ? 'Refresh + Copy Compact' : 'Refresh + Copy Capsule')
          : (primaryVariant === 'closeout_report' ? 'Prepare + Copy Compact' : 'Prepare + Copy Capsule');
    const closeoutActionText = selectedSourceWindow === SOURCE_WINDOW_FULL_THREAD_CONCISE ? 'Copy Thread Compact' : 'Copy Closeout Only';
    if (dropdownEls.missionCaptureCopy) {
      dropdownEls.missionCaptureCopy.disabled = !hasTraceTurn || copyReadiness.state === 'red' || capsuleCurrentness?.source_freshness?.action === 'block_copy';
      dropdownEls.missionCaptureCopy.textContent = copyActionText;
    }
    if (dropdownEls.missionPaneCopyCapsule) {
      dropdownEls.missionPaneCopyCapsule.disabled = !hasTraceTurn || copyReadiness.state === 'red' || capsuleCurrentness?.source_freshness?.action === 'block_copy';
      dropdownEls.missionPaneCopyCapsule.textContent = copyActionText.replace('Trace ', '');
    }
    if (dropdownEls.missionDownloadDenoised) {
      dropdownEls.missionDownloadDenoised.textContent = 'Save + Reveal';
      dropdownEls.missionDownloadDenoised.disabled = !hasTraceTurn;
    }
    if (dropdownEls.missionPaneSaveReveal) {
      dropdownEls.missionPaneSaveReveal.textContent = 'Save + Reveal';
      dropdownEls.missionPaneSaveReveal.disabled = !hasTraceTurn;
    }
    const marker = missionOperatorMarker(sel);
    if (dropdownEls.missionPanePin) {
      dropdownEls.missionPanePin.disabled = false;
      dropdownEls.missionPanePin.textContent = marker.pinned ? 'Unpin' : 'Pin';
    }
    if (dropdownEls.missionPaneSnooze) {
      dropdownEls.missionPaneSnooze.disabled = false;
      dropdownEls.missionPaneSnooze.textContent = marker.snoozed_until_ms && Number(marker.snoozed_until_ms) > Date.now() ? 'Unsnooze' : 'Snooze';
    }
    if (dropdownEls.missionPaneReviewed) {
      dropdownEls.missionPaneReviewed.disabled = false;
      dropdownEls.missionPaneReviewed.textContent = marker.reviewed_at_ms ? 'Reviewed' : 'Mark Reviewed';
    }
    if (dropdownEls.missionCopyCloseout) {
      dropdownEls.missionCopyCloseout.textContent = closeoutActionText;
      dropdownEls.missionCopyCloseout.disabled = !hasTraceTurn;
    }
    if (dropdownEls.missionPaneCopyCloseout) {
      dropdownEls.missionPaneCopyCloseout.textContent = closeoutActionText.replace(' Only', '');
      dropdownEls.missionPaneCopyCloseout.disabled = !hasTraceTurn;
    }
    // One operator-facing capsule state. Older packet/tape/index artifacts can
    // remain in the internal cache, but this surface deliberately has one copy target.
    const _setCell = (el, txt, cls) => {
      if (!el) return;
      el.textContent = txt;
      if (cls !== undefined) el.className = el.className.split(' ').filter(c => !['current','stale','missing','needs_capture','prepare_available','capture_failed','blocked','partial'].includes(c)).join(' ') + ' ' + cls;
    };
    const variantState = ({ artifact, currentness, readiness, canPrepare, partial, blockedReason, manifestReady }) => {
      if (readiness?.state === 'red') {
        const why = (readiness.blockers || []).slice(0, 2).join(', ') || 'copy readiness red';
        return { text: `BLOCKED: ${why}`, cls: 'blocked' };
      }
      if (artifact?.path && currentness?.ready) {
        return { text: 'READY', cls: 'current' };
      }
      if (artifact?.path && currentness?.source_freshness?.action === 'block_copy') {
        return { text: `BLOCKED: ${currentness.source_freshness.mismatch_reason || 'source mismatch'}`, cls: 'blocked' };
      }
      if (artifact?.path && currentness?.source_freshness?.action === 'refresh_before_copy') {
        return { text: `REFRESH REQUIRED: ${currentness.source_freshness.mismatch_reason || 'source mismatch'}`, cls: 'stale' };
      }
      if (artifact?.path && (currentness?.reason || '').includes('empty_trace')) {
        return { text: 'BLOCKED: EMPTY TRACE', cls: 'blocked' };
      }
      if (artifact?.path && canPrepare) {
        return { text: activeTrace ? 'CURRENT TRACE NOT PREPARED' : 'LATEST TRACE NOT PREPARED', cls: 'prepare_available' };
      }
      if (artifact?.path) return { text: 'STALE ARTIFACT', cls: 'stale' };
      if (manifestReady) return { text: 'MANIFEST READY', cls: 'current' };
      if (blockedReason) return { text: `BLOCKED: ${blockedReason}`, cls: 'blocked' };
      if (partial) return { text: 'PARTIAL', cls: 'partial' };
      if (isLiveSourceUpdating(sel) && canPrepare) return { text: 'PREPARE CURRENT', cls: 'prepare_available' };
      if (isSourceIndexStale(sel) && canPrepare) return { text: 'PREPARE LATEST', cls: 'prepare_available' };
      if (canPrepare) return { text: activeTrace ? 'PREPARE CURRENT' : 'PREPARE AVAILABLE', cls: 'prepare_available' };
      return { text: 'NO TURN', cls: 'partial' };
    };
    const capsuleState = variantState({
      artifact: capsuleArtifact,
      currentness: capsuleCurrentness,
      readiness: copyReadiness,
      canPrepare: hasTraceTurn,
      partial: !hasTraceTurn,
    });
    const exactSize = `${copySize.label}; ${closeoutReportSize(sel, selectedSourceWindow)}`;
    // Compact readiness badge only. The former multi-field coverage sentence
    // (commands / edits / validations / diff / diff gate / readiness / Type B /
    // artifact / totality / interventions / …) sat between the Trace Capsule
    // title and the scope rows as a wall of debug text. capsuleState.text still
    // carries the action plus raw mismatch reasons (REFRESH REQUIRED / BLOCKED /
    // READY …), so stale-source detection stays visible and the lifecycle
    // harness assertion on those reason tokens still holds.
    _setCell(dropdownEls.variantStateDenoised, capsuleState.text, 'trace-capsule-status ' + capsuleState.cls);
    _setCell(dropdownEls.variantBytesDenoised, exactSize);
    if (dropdownEls.variantBytesDenoised) {
      dropdownEls.variantBytesDenoised.title = capsuleArtifact?.path && capsuleCurrentness.ready
        ? `${capsuleArtifact.path} · ${capsuleKB}`
        : capsuleArtifact?.path
          ? `Stale ${primaryVariantLabel} is for another prompt/turn (${capsuleCurrentness.reason || 'identity mismatch'}). Prepare will write a current file.`
        : `No current ${primaryVariantLabel} file yet. Copy or Save + Reveal will materialize it and then update this size.`;
    }
    requestMissionSizeMeasurement(sel, selectedSourceWindow);
  } else {
    [
      dropdownEls.missionCaptureCopy,
      dropdownEls.missionCopyCloseout,
      dropdownEls.missionDownloadDenoised,
      dropdownEls.missionPaneCopyCapsule,
      dropdownEls.missionPaneCopyCloseout,
      dropdownEls.missionPaneSaveReveal,
      dropdownEls.missionPanePin,
      dropdownEls.missionPaneSnooze,
      dropdownEls.missionPaneReviewed,
    ].forEach((button) => { if (button) button.disabled = true; });
    renderMissionScopeContract(null, selectedSourceWindow);
  }
}

function safeRenderAgentTraceDropdown(reason = 'render') {
  if (shouldDeferMissionRenderForScroll(reason)) {
    return scheduleMissionRenderAfterScroll(reason);
  }
  try {
    renderAgentTraceDropdown(reason);
    return true;
  } catch (error) {
    const message = error?.message || String(error || 'unknown render error');
    try { console.error('[agent-trace-render]', reason, error); } catch (_) {}
    if (dropdownEls?.agentTraceRows) {
      dropdownEls.agentTraceRows.replaceChildren();
      const e = document.createElement('div');
      e.className = 'dropdown-empty';
      e.textContent = `Agent Trace render failed: ${message}`;
      dropdownEls.agentTraceRows.appendChild(e);
    }
    if (dropdownEls?.missionReceipt) {
      dropdownEls.missionReceipt.textContent = `✗ Agent Trace render failed (${String(reason || 'render').replace(/_/g, ' ')}): ${message}`;
    }
    setMissionRefreshControlsDisabled(false);
    return false;
  }
}

function coalesceMissionRenderReason(current = '', next = 'render') {
  const a = String(current || '');
  const b = String(next || 'render');
  if (!a) return b;
  const resetA = MISSION_SCROLL_RESET_REASONS.has(a) || a.includes('search') || a.includes('sort');
  const resetB = MISSION_SCROLL_RESET_REASONS.has(b) || b.includes('search') || b.includes('sort');
  if (resetB && !resetA) return b;
  if (resetA && !resetB) return a;
  if (b === 'mission_row_scroll' && a !== 'mission_row_scroll') return a;
  return b;
}

function scheduleMissionDropdownRender(reason = 'render') {
  missionRowsRenderQueuedReason = coalesceMissionRenderReason(missionRowsRenderQueuedReason, reason);
  if (missionRowsRenderRaf) return true;
  missionRowsRenderRaf = window.requestAnimationFrame(() => {
    const queuedReason = missionRowsRenderQueuedReason || reason || 'render';
    missionRowsRenderRaf = 0;
    missionRowsRenderQueuedReason = '';
    if (!isAgentTraceWorkbenchActive()) return;
    safeRenderAgentTraceDropdown(queuedReason);
  });
  return true;
}

function attachMissionRowsResizeObserver() {
  if (missionRowsResizeObserver || !dropdownEls?.agentTraceRows || typeof ResizeObserver !== 'function') return;
  missionRowsResizeObserver = new ResizeObserver(() => {
    if (!isAgentTraceWorkbenchActive()) return;
    scheduleMissionRowsScrollAffordanceUpdate();
    if (!lastMissionRowsRenderStats.windowed) return;
    scheduleMissionDropdownRender('mission_rows_resize');
  });
  missionRowsResizeObserver.observe(dropdownEls.agentTraceRows);
}

function updateMissionRowsScrollAffordance() {
  const container = dropdownEls?.agentTraceRows;
  const pane = missionListPaneEl();
  if (!container || !pane) return lastMissionRowsScrollAffordance;
  const maxScrollTop = Math.max(0, (container.scrollHeight || 0) - (container.clientHeight || 0));
  const top = Math.max(0, Math.min(container.scrollTop || 0, maxScrollTop));
  const scrollable = maxScrollTop > 1;
  const edge = !scrollable
    ? 'none'
    : (top <= 1 ? 'top' : (top >= maxScrollTop - 1 ? 'bottom' : 'middle'));
  pane.dataset.scrollable = scrollable ? 'true' : 'false';
  pane.dataset.scrollEdge = edge;
  lastMissionRowsScrollAffordance = {
    scrollable,
    edge,
    scroll_top: Math.round(top),
    max_scroll_top: Math.round(maxScrollTop),
  };
  return lastMissionRowsScrollAffordance;
}

function scheduleMissionRowsScrollAffordanceUpdate() {
  if (missionRowsScrollAffordanceRaf) return;
  missionRowsScrollAffordanceRaf = window.requestAnimationFrame(() => {
    missionRowsScrollAffordanceRaf = 0;
    updateMissionRowsScrollAffordance();
  });
}

function normalizeMissionRailWheelDelta(event, value, rail = missionRailEl) {
  const raw = Number(value) || 0;
  if (!raw) return 0;
  if (event.deltaMode === 1) return raw * MISSION_RAIL_WHEEL_LINE_PX;
  if (event.deltaMode === 2) return raw * Math.max(rail?.clientWidth || 0, window.innerWidth || 0) * MISSION_RAIL_WHEEL_PAGE_RATIO;
  return raw;
}

function clampMissionRailWheelDelta(rail, deltaPx) {
  const max = Math.max(0, (rail?.scrollWidth || 0) - (rail?.clientWidth || 0));
  if (!rail || max <= 1 || !Number.isFinite(deltaPx) || !deltaPx) return 0;
  const current = rail.scrollLeft || 0;
  const next = Math.max(0, Math.min(max, current + deltaPx));
  return next - current;
}

function handleMissionRailWheel(event) {
  const rail = missionRailEl;
  if (!rail || rail.scrollWidth <= rail.clientWidth + 1) return;
  const deltaX = normalizeMissionRailWheelDelta(event, event.deltaX, rail);
  const deltaY = normalizeMissionRailWheelDelta(event, event.deltaY, rail);
  const dominantY = Math.abs(deltaY) > Math.abs(deltaX);
  const intendedDelta = (event.shiftKey && deltaY) ? deltaY : (dominantY ? deltaY : deltaX);
  if (!intendedDelta) return;
  const limitedDelta = Math.max(
    -MISSION_RAIL_WHEEL_MAX_STEP_PX,
    Math.min(MISSION_RAIL_WHEEL_MAX_STEP_PX, intendedDelta * MISSION_RAIL_WHEEL_MULTIPLIER),
  );
  const ownedDelta = clampMissionRailWheelDelta(rail, limitedDelta);
  if (!ownedDelta) return;
  event.preventDefault();
  missionRailWheelDeltaX += ownedDelta;
  if (missionRailWheelRaf) return;
  missionRailWheelRaf = window.requestAnimationFrame(() => {
    const dx = missionRailWheelDeltaX;
    missionRailWheelDeltaX = 0;
    missionRailWheelRaf = 0;
    rail.scrollLeft += clampMissionRailWheelDelta(rail, dx);
  });
}

dropdownEls.missionCaptureCopy?.addEventListener('click', () => guardAgentTraceAction('copy_trace_capsule', () => {
  const sourceWindow = selectedTraceSourceWindow();
  const variant = tracePrimaryVariantForSource(sourceWindow);
  dropdownEls.missionReceipt.textContent = `Copying ${tracePrimaryVariantLabel(variant, sourceWindow)} from ${traceSourceWindowLabel(sourceWindow)}; closeout included when present...`;
  copySelectedMissionArtifact('compressed', variant);
}));
dropdownEls.missionPaneCopyCapsule?.addEventListener('click', () => guardAgentTraceAction('copy_trace_capsule_right_pane', () => {
  const sourceWindow = selectedTraceSourceWindow();
  const variant = tracePrimaryVariantForSource(sourceWindow);
  dropdownEls.missionReceipt.textContent = `Copying ${tracePrimaryVariantLabel(variant, sourceWindow)} from ${traceSourceWindowLabel(sourceWindow)}; closeout included when present...`;
  copySelectedMissionArtifact('compressed', variant);
}));
dropdownEls.missionCopyCloseout?.addEventListener('click', () => guardAgentTraceAction('copy_closeout_report', () => {
  dropdownEls.missionReceipt.textContent = `Copying closeout only from ${traceSourceWindowLabel(selectedTraceSourceWindow())}...`;
  copySelectedMissionArtifact('compressed', 'closeout_report');
}));
dropdownEls.missionPaneCopyCloseout?.addEventListener('click', () => guardAgentTraceAction('copy_closeout_report_right_pane', () => {
  dropdownEls.missionReceipt.textContent = `Copying closeout only from ${traceSourceWindowLabel(selectedTraceSourceWindow())}...`;
  copySelectedMissionArtifact('compressed', 'closeout_report');
}));
dropdownEls.missionSourceWindow?.addEventListener('change', () => guardAgentTraceAction('source_scope_change', () => {
  window.__aiwTraceSourceWindow = normalizeTraceSourceWindow(dropdownEls.missionSourceWindow.value);
  const row = findMissionByKey(selectedMissionKey);
  const metrics = row ? traceScopeMetrics(row, window.__aiwTraceSourceWindow) : null;
  dropdownEls.missionReceipt.textContent = metrics
    ? `Scope: ${metrics.label} · ${metrics.range} · ${metrics.byteLabel}${metrics.large ? ' · large/slow' : ''}`
    : `Scope: ${traceSourceWindowActionLabel(window.__aiwTraceSourceWindow)}`;
  safeRenderAgentTraceDropdown('source_window_change');
  updateAgentTraceSummary();
}));
dropdownEls.missionCopyTape?.addEventListener('click', () => {
  dropdownEls.missionReceipt.textContent = 'Copying dense tape...';
  copySelectedMissionArtifact('compressed', 'denoised');
});
dropdownEls.missionCopyCompact?.addEventListener('click', () => {
  dropdownEls.missionReceipt.textContent = 'Copying compact index...';
  // Sidecar index only: bounded navigation pointers, not the trace tape.
  copySelectedMissionArtifact('compressed', 'compact_json');
});
// v4 ← Compact returns to the closed system bar.
dropdownEls.agentTraceCompact?.addEventListener('click', () => {
  closeDropdown('compact_button');
});
// v4 save bridge. Swift writes the Trace Capsule text artifact to the managed
// AIW Captures export folder and asks Finder to reveal/select it.
dropdownEls.missionDownloadDenoised?.addEventListener('click', () => guardAgentTraceAction('save_reveal_trace_capsule', () => {
  const sourceWindow = selectedTraceSourceWindow();
  const variant = tracePrimaryVariantForSource(sourceWindow);
  dropdownEls.missionReceipt.textContent = `Saving ${tracePrimaryVariantLabel(variant, sourceWindow)} and opening Finder...`;
  downloadSelectedMissionArtifact(variant);
}));
dropdownEls.missionPaneSaveReveal?.addEventListener('click', () => guardAgentTraceAction('save_reveal_trace_capsule_right_pane', () => {
  const sourceWindow = selectedTraceSourceWindow();
  const variant = tracePrimaryVariantForSource(sourceWindow);
  dropdownEls.missionReceipt.textContent = `Saving ${tracePrimaryVariantLabel(variant, sourceWindow)} and opening Finder...`;
  downloadSelectedMissionArtifact(variant);
}));
dropdownEls.missionDownloadTape?.addEventListener('click', () => {
  dropdownEls.missionReceipt.textContent = 'Downloading dense tape...';
  downloadSelectedMissionArtifact('denoised');
});
dropdownEls.missionDownloadCompact?.addEventListener('click', () => {
  dropdownEls.missionReceipt.textContent = 'Downloading compact index...';
  downloadSelectedMissionArtifact('compact_json');
});
dropdownEls.missionDownloadFull?.addEventListener('click', () => {
  dropdownEls.missionReceipt.textContent = 'Downloading full JSON…';
  downloadSelectedMissionArtifact('full_json');
});
function downloadSelectedMissionArtifact(variant) {
  return guardAgentTraceAction('download_selected_mission', () => downloadSelectedMissionArtifactUnsafe(variant));
}

function downloadSelectedMissionArtifactUnsafe(variant) {
  const sel = findMissionByKey(selectedMissionKey);
  if (!sel) {
    dropdownEls.missionReceipt.textContent = '✗ no mission selected';
    return;
  }
  const lct = rowHasActiveTrace(sel) ? activityDisplayTurn(sel) : traceDisplayTurn(sel);
  const activeTrace = rowHasActiveTrace(sel);
  const sourceWindow = selectedTraceSourceWindow();
  const backendSourceWindow = backendTraceSourceWindow(sourceWindow);
  const traceWindow = traceWindowForSource(sel, sourceWindow, lct);
  const promptSha16 = backendSourceWindow === SOURCE_WINDOW_SELECTED_TURN
    ? (lct.prompt_sha16 || '')
    : (backendSourceWindow === SOURCE_WINDOW_FULL_THREAD
      ? (traceWindow.prompt_sha16 || lct.full_thread_prompt_sha16 || '')
      : (traceWindow.prompt_sha16 || lct.trace_window_prompt_sha16 || lct.prompt_sha16 || ''));
  const turnIndex = backendSourceWindow === SOURCE_WINDOW_SELECTED_TURN ? (lct.turn_index ?? null) : (traceWindow.end_turn_index ?? lct.turn_index ?? null);
  const turnId = backendSourceWindow === SOURCE_WINDOW_SELECTED_TURN ? (lct.turn_id || '') : (traceWindow.turn_id || lct.trace_window_turn_id || lct.turn_id || '');
  postNative('downloadMissionArtifact', {
    mission_key: selectedMissionKey,
    variant,
    title: missionDisplayTitle(sel, lct),
    provider: sel.provider || '',
    session_id: sel.session_id || '',
    prompt_sha16: promptSha16,
    turn_index: turnIndex,
    turn_id: turnId,
    expected_prompt_sha16: promptSha16,
    expected_turn_index: turnIndex,
    expected_turn_id: turnId,
    window_start_turn_index: backendSourceWindow === SOURCE_WINDOW_SELECTED_TURN ? (lct.turn_index ?? null) : (traceWindow.start_turn_index ?? lct.turn_index ?? null),
    window_turn_count: backendSourceWindow === SOURCE_WINDOW_SELECTED_TURN ? 1 : (traceWindow.turn_count || (backendSourceWindow === SOURCE_WINDOW_FULL_THREAD ? lct.full_thread_turn_count : lct.trace_window_turn_count) || 1),
    use_active_turn: activeTrace,
    allow_partial: activeTrace,
    source_window: backendSourceWindow,
    ui_source_window: sourceWindow,
    include_source_excerpts: true,
    ...traceIdentityPolicy(sel, activeTrace),
  });
}
window.agentTraceStructurerDownloadResult = (data) => {
  if (data?.ok) {
    rememberVariantArtifact(data);
    const exactSize = _formatExactSize(data.bytes || 0);
    const scope = data.storage_scope === 'managed_visible_export' ? 'AIW Captures' : 'Finder';
    dropdownEls.missionReceipt.textContent = `✓ Saved + revealed ${data.variant} · ${data.title || ''} · ${exactSize} · ${scope} · ${data.path || ''}`;
	    safeRenderAgentTraceDropdown('download_result');
    updateAgentTraceSummary();
  } else {
    dropdownEls.missionReceipt.textContent = `✗ download ${data?.variant || ''}: ${data?.error || 'failed'}`;
  }
};
// v8 Full JSON: when raw source is large (>512KB), the primary click
// puts a small manifest on the pasteboard instead of the multi-MB file.
// The data attribute `data-full-mode` is set by renderAgentTraceDropdown
// to either 'manifest' or 'inline' based on size threshold.
dropdownEls.missionCopyFull?.addEventListener('click', () => guardAgentTraceAction('copy_full_thread', () => {
  const sel = findMissionByKey(selectedMissionKey);
  if (!sel) return;
  const mode = dropdownEls.missionCopyFull.dataset.fullMode || 'inline';
  if (mode === 'manifest') {
    dropdownEls.missionReceipt.textContent = 'Copying full manifest…';
    postNative('copyVariantManifest', {
      session_id: sel.session_id, title: missionDisplayTitle(sel, traceDisplayTurn(sel)),
      variant: 'full_json',
      source_window: backendTraceSourceWindow(selectedTraceSourceWindow()),
      ui_source_window: selectedTraceSourceWindow(),
    });
  } else {
    dropdownEls.missionReceipt.textContent = 'Copying full…';
    copySelectedMissionArtifact('full');
  }
}));
// v8 Reveal: route to revealMissionSource Swift bridge which uses
// NSWorkspace.activateFileViewerSelecting on the session_file (raw
// JSONL) path. Previously this called revealSelectedMission which only
// looked at artifact_refs and gave up when no derived artifact existed,
// even though the raw source IS always available.
dropdownEls.missionReveal?.addEventListener('click', () => guardAgentTraceAction('reveal_mission_source', () => {
  const sel = findMissionByKey(selectedMissionKey);
  if (!sel) return;
  dropdownEls.missionReceipt.textContent = 'Revealing raw source…';
  postNative('revealMissionSource', {
    session_id: sel.session_id, title: missionDisplayTitle(sel, traceDisplayTurn(sel)),
    variant: 'raw_jsonl',
  });
}));
window.agentTraceStructurerRevealResult = (data) => {
  if (data?.ok) {
    const kb = Math.round((data.bytes || 0) / 1024 * 10) / 10;
    dropdownEls.missionReceipt.textContent = `✓ Revealed ${data.variant || ''} · ${data.title || ''} · ${kb} KB · ${data.path || ''}`;
  } else {
    dropdownEls.missionReceipt.textContent = `✗ reveal ${data?.variant || ''}: ${data?.error || 'failed'}${data?.tried_path ? ' (tried: ' + data.tried_path + ')' : ''}`;
  }
};
window.agentTraceStructurerManifestCopy = (data) => {
  if (data?.ok) {
    const kb = Math.round((data.manifest_bytes || 0) / 1024 * 10) / 10;
    const artKB = Math.round((data.artifact_bytes || 0) / 1024 * 10) / 10;
    dropdownEls.missionReceipt.textContent = `✓ Copied ${data.variant} manifest (${kb} KB pointing at ${artKB} KB artifact) · ${data.title || ''}`;
  } else {
    dropdownEls.missionReceipt.textContent = `✗ manifest ${data?.variant || ''}: ${data?.error || 'failed'}`;
  }
};
window.agentTraceStructurerMissionMeasure = (data) => {
  const row = findMissionByKey(data?.mission_key || selectedMissionKey);
  if (data?.measurement_key) missionSizeMeasurementsPending.delete(data.measurement_key);
  if (!data?.ok || !row) return;
  const measurements = data.measurements || {};
  const measuredAt = Date.now();
  for (const [variant, byWindow] of Object.entries(measurements)) {
    if (!byWindow || typeof byWindow !== 'object') continue;
    if (!['trace_capsule', 'closeout_report'].includes(variant)) continue;
    for (const [sourceWindow, measurement] of Object.entries(byWindow)) {
      const bytes = _numberOrNull(measurement?.bytes);
      if (!bytes || bytes <= 0) continue;
      const windows = new Set([sourceWindow]);
      const uiWindow = normalizeTraceSourceWindow(data.ui_source_window || data.requested_source_window || '');
      if (
        uiWindow
        && backendTraceSourceWindow(uiWindow) === backendTraceSourceWindow(sourceWindow)
        && tracePrimaryVariantForSource(uiWindow) === variant
      ) {
        windows.add(uiWindow);
      }
      for (const identityWindow of windows) {
        const identity = selectedSourceIdentity(row, variant, identityWindow);
        if (!identity.identity_key) continue;
        missionSizeMeasurements.set(identity.identity_key, {
          bytes,
          sha16: measurement.sha16 || '',
          source: 'native_current_measure',
          measuredAt,
        });
        missionSizeMeasurementsPending.delete(identity.identity_key);
      }
    }
  }
  if (isAgentTraceWorkbenchActive()) safeRenderAgentTraceDropdown('mission_measure_result');
  updateAgentTraceSummary();
};
dropdownEls.agentTraceSort?.addEventListener('change', (e) => {
	  dropdownSortMode = e.target.value;
	  safeRenderAgentTraceDropdown('sort_change');
});
dropdownEls.agentTraceSearch?.addEventListener('input', (e) => {
	  dropdownSearch = e.target.value || '';
	  if (missionSearchRenderTimer) window.clearTimeout(missionSearchRenderTimer);
	  // v7/v8: value updates eagerly (keeps inactive-row include logic correct);
	  // debounce + RAF-coalesce the heavy render so typing does not fight scroll.
	  missionSearchRenderTimer = window.setTimeout(() => {
	    missionSearchRenderTimer = 0;
	    scheduleMissionDropdownRender('search_input');
	  }, MISSION_SEARCH_DEBOUNCE_MS);
});
dropdownEls.agentTraceSearch?.addEventListener('keydown', (event) => {
  const key = String(event.key || '').toLowerCase();
  if ((event.metaKey || event.ctrlKey) && !event.altKey && key === 'a') {
    event.preventDefault();
    event.stopPropagation();
    event.currentTarget?.select?.();
    window.__aiwLastMissionSearchSelectAll = {
      ok: true,
      at: new Date().toISOString(),
      value: event.currentTarget?.value || '',
    };
    return;
  }
  if (key === 'enter') {
    const match = bestMissionSearchMatch(event.currentTarget?.value || dropdownSearch);
    if (!match) return;
    event.preventDefault();
    selectMission(missionKey(match));
    safeRenderAgentTraceDropdown('search_enter_select');
    updateAgentTraceSummary();
  }
});
dropdownEls.agentTraceRefresh?.addEventListener('click', () => {
  refreshMissionIndexClick();
});
dropdownEls.missionPaneRefresh?.addEventListener('click', () => {
  refreshMissionIndexClick();
});
dropdownEls.missionPanePin?.addEventListener('click', () => guardAgentTraceAction('toggle_mission_pin', () => {
  const row = findMissionByKey(selectedMissionKey);
  if (!row) return;
  const marker = missionOperatorMarker(row);
  const next = setMissionOperatorMarker(row, {
    pinned: !marker.pinned,
    marker_kind: !marker.pinned ? 'pinned' : 'unpinned',
  });
  setMissionReceipt(`${next?.pinned ? 'Pinned' : 'Unpinned'} ${missionDisplayTitle(row, activityDisplayTurn(row))} in the review queue.`);
  safeRenderAgentTraceDropdown('operator_marker_pin');
}));
dropdownEls.missionPaneSnooze?.addEventListener('click', () => guardAgentTraceAction('toggle_mission_snooze', () => {
  const row = findMissionByKey(selectedMissionKey);
  if (!row) return;
  const marker = missionOperatorMarker(row);
  const active = marker.snoozed_until_ms && Number(marker.snoozed_until_ms) > Date.now();
  const patch = active
    ? { snoozed_until_ms: 0, marker_kind: 'unsnoozed' }
    : { snoozed_until_ms: Date.now() + 2 * 60 * 60_000, marker_kind: 'snoozed_2h' };
  setMissionOperatorMarker(row, patch);
  setMissionReceipt(`${active ? 'Unsnoozed' : 'Snoozed for 2h'} ${missionDisplayTitle(row, activityDisplayTurn(row))}.`);
  safeRenderAgentTraceDropdown('operator_marker_snooze');
}));
dropdownEls.missionPaneReviewed?.addEventListener('click', () => guardAgentTraceAction('mark_mission_reviewed', () => {
  const row = findMissionByKey(selectedMissionKey);
  if (!row) return;
  setMissionOperatorMarker(row, {
    reviewed_at_ms: Date.now(),
    marker_kind: 'reviewed',
    follow_up_due_at_ms: Date.now() + 25 * 60_000,
  });
  setMissionReceipt(`Marked reviewed; follow-up due in 25m for ${missionDisplayTitle(row, activityDisplayTurn(row))}.`);
  safeRenderAgentTraceDropdown('operator_marker_reviewed');
}));
window.agentTraceStructurerMissionOperatorMarker = (data) => {
  if (!data?.ok || !data.mission_key) return;
  if (data.marker && typeof data.marker === 'object') {
    missionOperatorMarkers[data.mission_key] = data.marker;
  }
  persistMissionOperatorMarkers();
};
dropdownEls.missionPaneToggleInactive?.addEventListener('click', () => {
  showInactiveMissions = !showInactiveMissions;
  safeRenderAgentTraceDropdown('toggle_inactive_missions');
});

function handleMissionRowsClick(event) {
  const container = dropdownEls?.agentTraceRows;
  if (!container) return;
  const target = event.target;
  const subagentToggle = target?.closest?.('[data-subagent-toggle]');
  if (subagentToggle && container.contains(subagentToggle)) {
    settleMissionRowsInteractionNow();
    event.preventDefault();
    event.stopPropagation();
    const toggled = toggleMissionSubagents(subagentToggle.getAttribute('data-subagent-toggle'));
    if (toggled) safeRenderAgentTraceDropdown('subagent_toggle');
    return;
  }
  const subagentRow = target?.closest?.('.dropdown-row.subagent-row[data-mission-key]');
  if (subagentRow && container.contains(subagentRow)) {
    const childMissionKey = subagentRow.dataset.childMissionKey || '';
    const parentMissionKey = subagentRow.dataset.missionKey || '';
    const key = childMissionKey || parentMissionKey;
    if (!key) return;
    settleMissionRowsInteractionNow();
    selectMission(key);
    safeRenderAgentTraceDropdown(childMissionKey ? 'subagent_child_row_select' : 'subagent_row_select');
    updateAgentTraceSummary();
    return;
  }
  const row = target?.closest?.('.dropdown-row[data-mission-key]');
  if (!row || !container.contains(row) || row.classList.contains('row-error')) return;
  const key = row.dataset.missionKey || '';
  if (!key) return;
  settleMissionRowsInteractionNow();
  selectMission(key);
  safeRenderAgentTraceDropdown('row_select');
  updateAgentTraceSummary();
}

dropdownEls.agentTraceRows?.addEventListener('click', (event) => guardAgentTraceAction('mission_rows_click', () => {
  handleMissionRowsClick(event);
}));

dropdownEls.agentTraceRows?.addEventListener('scroll', () => {
  markMissionRowsUserScrolling(dropdownEls.agentTraceRows?.scrollTop || 0);
  scheduleMissionRowsScrollAffordanceUpdate();
  // Native scrolling is smooth on its own. The list only needs to re-render when
  // it is virtualized (windowed) AND a new slice of rows scrolls into view.
  // Re-rendering (full replaceChildren) on every animation frame fights the
  // browser's own scroll position, so virtual slices advance in small row chunks.
  // For the common, un-windowed case (< MISSION_WINDOWING_MIN_ROWS rows) scrolling
  // is a no-op.
  if (!lastMissionRowsRenderStats.windowed) return;
  if (missionRowsScrollRaf) return;
  missionRowsScrollRaf = window.requestAnimationFrame(() => {
    missionRowsScrollRaf = 0;
    if (!isAgentTraceWorkbenchActive()) return;
    if (!missionScrollWindowChanged()) return;
    scheduleMissionDropdownRender('mission_row_scroll');
  });
}, { passive: true });

missionRailEl?.addEventListener('wheel', handleMissionRailWheel, { passive: false });

const _origLatestClipCallback = window.agentTraceStructurerLatestClipCopy;
window.agentTraceStructurerLatestClipCopy = (data) => {
  if (typeof _origLatestClipCallback === 'function') _origLatestClipCallback(data);
  if (data?.ok) {
    const kb = Math.round((data.copied_bytes || 0) / 1024 * 10) / 10;
    dropdownEls.clipboardReceipt.textContent = `✓ ${data.row_kind || 'clip'} · ${kb} KB`;
  } else {
    dropdownEls.clipboardReceipt.textContent = `✗ ${data?.stage || ''} ${data?.error || ''}`.trim();
  }
};
const _origMissionLatestCopy = window.agentTraceStructurerMissionLatestCopy;
window.agentTraceStructurerMissionLatestCopy = (data) => {
  window.__aiwLastMissionLatestCopy = data || null;
  const pendingCopyAnchor = pendingMissionCopyAnchor;
  const callbackAnchor = pendingCopyAnchor
    || {
      key: data?.mission_key || missionKeyFromParts(data?.ui_provider || data?.provider, data?.session_id),
      provider: data?.ui_provider || data?.provider || '',
      session_id: data?.session_id || '',
      title: data?.title || '',
      prompt_sha16: data?.prompt_sha16 || '',
      turn_index: data?.turn_index ?? null,
    };
  if (data?.ok && !pendingCopyAnchor) {
    const error = 'copy callback missing pending mission proof';
    setMissionReceipt(`✗ ${error}`, 'copy_error');
    rememberMissionCopyFailure(callbackAnchor?.key, error);
    safeRenderAgentTraceDropdown('latest_copy_missing_anchor');
    updateAgentTraceSummary();
    return;
  }
  if (data && typeof data === 'object' && !data.ui_source_window) {
    data.ui_source_window = callbackAnchor?.copiedSourceWindow || selectedTraceSourceWindow();
  }
  const callbackMismatch = missionCopyCallbackMismatch(data, callbackAnchor);
  if (callbackMismatch) {
    restoreMissionAnchor(callbackAnchor);
    setMissionReceipt(`✗ ${callbackMismatch}`, 'copy_error');
    rememberMissionCopyFailure(callbackAnchor?.key, callbackMismatch);
    clearPendingMissionCopyAnchor(callbackAnchor);
    safeRenderAgentTraceDropdown('latest_copy_mismatch');
    updateAgentTraceSummary();
    return;
  }
  restoreMissionAnchor(callbackAnchor);
  if (typeof _origMissionLatestCopy === 'function') _origMissionLatestCopy(data);
  if (data?.ok) {
    restoreMissionAnchor(callbackAnchor);
    selectedMissionAnchor = callbackAnchor;
    holdPendingMissionCopyAnchor(callbackAnchor);
    rememberVariantArtifact(data);
    const copiedBytes = Number(data.copied_bytes || 0);
    const sha = data.prompt_sha16 ? ` · ${data.prompt_sha16.slice(0, 8)}` : '';
    // v5 receipt identity fix: prefer the SELECTED mission's title over
    // Swift's filename-derived data.title (which can read as 'old 17' for
    // 17,18 traces because of clip filename tokens). Native callback title
    // moves to debug-only.
    const selRow = findMissionByKey(selectedMissionKey);
    const displayTitle = (selRow && missionDisplayTitle(selRow, traceDisplayTurn(selRow))) || data.title || '';
    // v12.1: surface the exact slice/standalone identity in the receipt
    // so the operator can see what just landed on the pasteboard.
    let variantTag = '';
    if (data.slice_label === 'agent_trace_capsule_text_v3') variantTag = ' · Trace Capsule text v3';
    else if (data.slice_label === 'agent_trace_capsule_text_v2') variantTag = ' · Trace Capsule text v2';
    else if (data.slice_label === 'agent_trace_capsule_text_v1') variantTag = ' · Trace Capsule text v1';
    else if (data.slice_label === 'agent_trace_closeout_report_v1') variantTag = ' · Closeout Report v1';
    else if (data.slice_label === 'agent_trace_packet_v1') variantTag = ' · Trace Packet v1 (summary, progress, commands, edits, tests)';
    else if (data.slice_label === 'trace_tape_v1') variantTag = ' · Trace Tape v1 (commands, outputs, edits, tests)';
    else if (data.slice_label === 'denoised_v1') variantTag = ' · Trace Handoff v1 (legacy packet)';
    else if (data.slice_label === 'denoised_v0') variantTag = ' · Denoised Handoff v0 (stale summary shape)';
    else if (data.slice_label === 'compact_json_v2') variantTag = ' · Compact Index v2 (columnar JSON)';
    else if (data.slice_label === 'compact_json_v1') variantTag = ' · Compact Index v1 (legacy bounded JSON)';
    else if (data.slice_label === 'compact_json_v0') variantTag = ' · Compact Evidence v0 (legacy sidecar)';
    else if (data.slice_label) variantTag = ` · ${data.slice_label}`;
    const successMeta = {
      copiedBytes,
      copiedVariantLabel: callbackAnchor?.copiedVariantLabel || tracePrimaryVariantLabel(data.variant || tracePrimaryVariantForSource(data.ui_source_window), data.ui_source_window),
      copiedSourceWindowLabel: callbackAnchor?.copiedSourceWindowLabel || (data.ui_source_window ? traceSourceWindowLabel(data.ui_source_window) : ''),
      copiedRangeLabel: callbackAnchor?.copiedRangeLabel || '',
      copiedTurnIndex: data.turn_index ?? callbackAnchor?.copiedTurnIndex ?? callbackAnchor?.turn_index ?? null,
      copiedTurnCompletedAt: callbackAnchor?.copiedTurnCompletedAt || '',
      copiedTurnStartedAt: callbackAnchor?.copiedTurnStartedAt || '',
      copiedTurnInFlight: Boolean(callbackAnchor?.copiedTurnInFlight),
      copiedSliceLabel: data.slice_label || '',
    };
    const copiedSourceWatermark = data?.copied_source_watermark || data?.source_watermark || data?.variant_artifact?.copied_source_watermark || data?.variant_artifact?.source_watermark || {};
    successMeta.copiedSourceWatermarkId = copiedSourceWatermark?.watermark_id || '';
    successMeta.copiedSourceMtimeUtc = copiedSourceWatermark?.mtime_utc || '';
    if (!successMeta.copiedTurnCompletedAt && selRow) {
      const copiedTurn = activityDisplayTurn(selRow);
      if (Number(copiedTurn?.turn_index) === Number(successMeta.copiedTurnIndex)) {
        successMeta.copiedTurnCompletedAt = copiedTurn.completed_at || '';
        successMeta.copiedTurnInFlight = traceTurnLooksActive(copiedTurn);
      }
    }
    // The native callback signals the pasteboard write completed — NOT that
    // the downstream agent "returned". rememberMissionCopySuccess starts the
    // pending_after_copy window which clears the moment the source mission
    // emits new activity (last_activity_at > successAt) or the agent goes live.
    rememberMissionCopySuccess(callbackAnchor?.key, successMeta);
    const copySummary = missionCopySummary(successMeta, Date.now(), { includeScope: true });
    const receiptModel = selRow ? missionStateModel(selRow, data.ui_source_window || selectedTraceSourceWindow()) : null;
    const receiptTrust = receiptModel ? [
      receiptModel.thread_totality ? `scope=${receiptModel.thread_totality}` : '',
      receiptModel.copy_policy?.header_warning || '',
      receiptModel.copy_policy?.risk_if_latest_only || '',
      receiptModel.diff_state ? `diff ${String(receiptModel.diff_state).replace(/_/g, ' ')}` : '',
      receiptModel.source_freshness_action ? `copy ${String(receiptModel.source_freshness_action).replace(/_/g, ' ')}` : '',
      successMeta.copiedSourceWatermarkId ? `source ${successMeta.copiedSourceWatermarkId.slice(0, 8)}` : '',
      receiptModel.stats_source?.label ? `stats ${receiptModel.stats_source.label}` : '',
      receiptModel.operator_interventions ? `interventions selected=${receiptModel.operator_interventions.selected_window_count ?? 'unknown'} full=${receiptModel.operator_interventions.full_thread_count ?? 'unknown'}` : '',
    ].filter(Boolean).join(' · ') : '';
    const receiptText = `✓ COPIED ${successMeta.copiedVariantLabel || 'trace'} · ${displayTitle}${copySummary ? ` · ${copySummary}` : ''}${receiptTrust ? ` · ${receiptTrust}` : ''}${sha}${variantTag}`;
    setMissionReceipt(receiptText, 'copy_success');
    setMissionBarStatus(receiptText, { timeoutMs: MISSION_COPY_ACK_MS });
    safeRenderAgentTraceDropdown('latest_copy_result');
    updateAgentTraceSummary();
  } else {
    restoreMissionAnchor(callbackAnchor);
    const reason = missionLatestCopyFailureReason(data);
    setMissionReceipt(`✗ ${reason}`, 'copy_error');
    rememberMissionCopyFailure(callbackAnchor?.key, reason);
    clearPendingMissionCopyAnchor(callbackAnchor);
  }
};
const _origMissionIndexCallback = window.agentTraceStructurerMissionIndex;
window.agentTraceStructurerMissionIndex = (data) => {
  const pendingCopyAnchor = pendingMissionCopyAnchor;
  const anchorBeforeRefresh = pendingCopyAnchor || selectedMissionAnchor;
  const selectedBeforeRefresh = selectedMissionKey;
  if (pendingCopyAnchor) restoreMissionAnchor(pendingCopyAnchor);
  if (typeof _origMissionIndexCallback === 'function') _origMissionIndexCallback(data);
  const restored = restoreMissionAnchor(pendingCopyAnchor || anchorBeforeRefresh);
  updateAgentTraceSummary();
  if (restored && selectedMissionKey !== selectedBeforeRefresh && isAgentTraceWorkbenchActive()) {
    safeRenderAgentTraceDropdown('mission_anchor_restore');
  }
  renderMissionRail();
  scheduleMissionFinishedAutoRefresh();
};
const _origCaptureHistoryCallback = window.agentTraceStructurerCaptureHistory;
window.agentTraceStructurerCaptureHistory = (payload) => {
  if (typeof _origCaptureHistoryCallback === 'function') _origCaptureHistoryCallback(payload);
  updateLatestClipSummary();
  if (activeDropdown === 'clipboard') renderClipboardDropdown();
};

updateLatestClipSummary();
updateAgentTraceSummary();

// === Mission Chooser v1 surface ===
// Expose the JS data + dropdown control surface so the Swift runtime probe
// can read mission rows without requiring the dropdown to be open, and so
// external smokes / DevTools can drive the chooser programmatically.
window.__aiwSystemBar = {
  missionRows: () => allMissionRows(),
  missionSchema: () => (missionIndex && missionIndex.schema) || '',
  selectedTitle: () => {
    const row = findMissionByKey(selectedMissionKey);
    return row ? missionDisplayTitle(row, traceDisplayTurn(row)) : '';
  },
  selectedKey: () => selectedMissionKey,
  selectedAnchor: () => selectedMissionAnchor,
  openDropdown,
  closeDropdown,
  closeCallLog: () => _closeCallLog.slice(),
  closeCallCount: () => _closeCallLog.length,
  lastCloseReason: () => (_closeCallLog.length ? _closeCallLog[_closeCallLog.length - 1].reason : null),
  interactionState: () => ({
    activeDropdown,
    mode: document.body.dataset.systembarMode || '',
    nativeMode: document.body.dataset.nativeWindowMode || '',
    shellMode: document.body.dataset.nativeShellMode || '',
    pinned: systemBarPinned,
    hover: systemBarHover,
    expanded: systemBarExpanded,
    dragging: Boolean(toolbarDrag),
    compactHoverQueued: Boolean(systemBarCompactHoverTimer),
    collapseQueued: Boolean(systemBarCollapseTimer),
  }),
  expandFromNativeCompactClick: expandSystemBarFromNativeCompactClick,
  syncNativeWindowMode,
  setShellMode,
  toggleDropdown,
  setSearch: (q) => {
    dropdownSearch = String(q || '');
    if (dropdownEls?.agentTraceSearch && dropdownEls.agentTraceSearch.value !== dropdownSearch) {
      dropdownEls.agentTraceSearch.value = dropdownSearch;
    }
    safeRenderAgentTraceDropdown('api_search');
  },
  missionSearchDiagnostics: (q = dropdownSearch) => {
    const query = String(q || '');
    const rows = sortedMissionRows(query.trim() ? allMissionRows() : visibleMissionRows())
      .map((row) => ({ row, score: missionSearchScore(row, query) }))
      .filter((entry) => entry.score > 0)
      .sort((a, b) => (b.score - a.score)
        || (_missionSortTime(b.row) - _missionSortTime(a.row))
        || ((b.row.mission_ordinal_key || 0) - (a.row.mission_ordinal_key || 0)));
    const top = rows[0]?.row || null;
    return {
      query,
      count: rows.length,
      top_key: top ? missionKey(top) : '',
      top_title: top ? missionDisplayTitle(top, activityDisplayTurn(top)) : '',
      top_score: rows[0]?.score || 0,
      top_source: top ? missionSearchMatchSource(top, query, rows[0]?.score || 0) : '',
      provenance: dropdownEls?.agentTraceSearchProvenance?.textContent || '',
    };
  },
  setSort: (m) => { dropdownSortMode = String(m || DEFAULT_AGENT_TRACE_SORT_MODE); safeRenderAgentTraceDropdown('api_sort'); },
  setSourceWindow: (value) => {
    const normalizedRaw = normalizeTraceSourceWindow(value);
    const normalized = normalizedRaw === SOURCE_WINDOW_SELECTED_TURN ? DEFAULT_TRACE_SOURCE_WINDOW : normalizedRaw;
    window.__aiwTraceSourceWindow = normalized;
    if (dropdownEls?.missionSourceWindow) dropdownEls.missionSourceWindow.value = normalized;
    safeRenderAgentTraceDropdown('api_source_window');
    updateAgentTraceSummary();
    return normalized;
  },
  selectedSourceWindow: () => selectedTraceSourceWindow(),
  selectedMissionStateModel: () => {
    const row = findMissionByKey(selectedMissionKey);
    return row ? missionStateModel(row, selectedTraceSourceWindow()) : null;
  },
  sourceScopeContract: () => {
    const row = findMissionByKey(selectedMissionKey);
    const sourceWindow = selectedTraceSourceWindow();
    return TRACE_OPERATOR_SOURCE_WINDOWS
      .map((value) => traceScopeMetrics(row, value))
      .map((m) => ({ ...m, selected: m.sourceWindow === sourceWindow }));
  },
  missionRenderStats: () => ({ ...lastMissionRowsRenderStats }),
  missionRowsScrollSettling: () => missionRowsScrollSettling(),
  missionRowsScrollProfile: () => ({
    ...lastMissionRowsScrollProfileStats,
    fast_scrolling: missionRowsFastScrolling(),
  }),
  missionRowsDeferredRenderState: () => ({
    ...lastMissionRowsDeferredRenderStats,
    pending: Boolean(missionRowsDeferredRenderTimer),
    queued_reason: missionRowsDeferredRenderReason,
  }),
  missionRowsScrollAffordance: () => ({ ...lastMissionRowsScrollAffordance }),
  uncaughtErrorCount: () => missionUncaughtErrors.length,
  uncaughtErrors: () => missionUncaughtErrors.slice(),
  expandedSubagentParents: () => Array.from(expandedSubagentParentKeys),
  expandedSubagentParentVersion: () => expandedSubagentParentVersion,
  toggleSubagents: (k) => {
    const toggled = toggleMissionSubagents(k);
    if (toggled) safeRenderAgentTraceDropdown('api_toggle_subagents');
    return toggled;
  },
  selectMission: (k) => {
    clearPendingMissionCopyAnchor();
    selectedMissionKey = String(k || '');
    rememberSelectedMissionAnchor();
    safeRenderAgentTraceDropdown('api_select_mission');
    updateAgentTraceSummary();
  },
};
window.agentTraceStructurerMissionRenderStats = () => window.__aiwSystemBar.missionRenderStats();

// v8 sticky workbench event model. In agent_trace mode the surface is a
// workbench (not a transient popover); internal clicks NEVER compact.
// Only ← Compact button + Esc closes. Latest Clip remains a popover and
// keeps outside-click-to-close behavior.
document.addEventListener('mousedown', (event) => {
  if (!activeDropdown) return;
  const panel = dropdownEls.panel;
  const triggers = [dropdownEls.latestClipTrigger, dropdownEls.agentTraceTrigger, dropdownEls.promptsTrigger, els.buttons.operatorHud];
  // Internal panel click: never close (any mode).
  if (panel && panel.contains(event.target)) return;
  // Trigger click is routed by the toggle handler; do not double-close.
  if (triggers.some(t => t && t.contains(event.target))) return;
  // v8: in workbench mode, outside-click does NOT close. The operator
  // must use the explicit ← Compact button or Esc. This stops the
  // collapse-on-anything regression and matches workbench semantics
  // (durable local state while open).
  if (isAgentTraceWorkbenchActive()) return;
  // Latest Clip popover keeps the outside-close behavior.
  closeDropdown('outside_click');
}, { capture: true });
// Additional belt-and-suspenders: stop any internal pointerdown from
// reaching document-level handlers that might close the workbench.
dropdownEls.panel?.addEventListener('pointerdown', (e) => { e.stopPropagation(); }, { capture: true });

// Esc closes the dropdown.
document.addEventListener('keydown', (event) => {
  if (event.key !== 'Escape') return;
  if (windowsPopupOpen) {
    closeWindowsPopup('escape_key');
    event.preventDefault();
    event.stopPropagation();
    return;
  }
  if (!activeDropdown) return;
  closeDropdown('escape_key');
  event.preventDefault();
});

// Auto-probe on app start so last_runtime_probe.json is always fresh and
// external smokes can verify the visible state without operator clicks.
// First probe: closed-state baseline.
// Second probe (after a tick): open Agent Trace, snapshot rendered rows
// including 17,18, then close. This way the disk receipt proves both
// closed-state and open-state correctness without operator interaction.
// v4 clipboard-sanctity gate: copy/click-mutating smokes only fire when
// window.__aiwSmokeEnabled is true (Swift sets this from AIW_ATS_SMOKE=1
// env at document start). Read-only probes are always-on so the runtime
// probe disk receipt stays fresh for external diagnostics.
window.setTimeout(() => {
  postNative('runtimeSystemBarProbe');
}, 1200);
if (window.__aiwSmokeEnabled) {
  const smokeAction = window.__aiwSmokeAction || 'selected-row-copy';
  window.setTimeout(() => {
    postNative('runtimeSystemBarProbe', { openMode: 'agent_trace' });
  }, 2400);
  window.setTimeout(() => {
    postNative('realClickSmoke', { target: '#agent-trace-trigger' });
  }, 3600);
  window.setTimeout(() => {
    const payload = {
      match: window.__aiwSmokeMatch || '17, 18',
      variant: window.__aiwSmokeVariant || 'trace_capsule',
      source_window: window.__aiwSmokeSourceWindow || DEFAULT_TRACE_SOURCE_WINDOW,
      action: smokeAction,
    };
    if (smokeAction === 'workbar-copy') {
      postNative('workbarCopySmoke', payload);
    } else {
      postNative('selectedRowCopySmoke', payload);
    }
  }, 5000);
}
window.agentTraceStructurerSelectedRowCopySmoke = (data) => {
  try { console.log('[selected-row copy smoke]', data?.gated_off ? 'GATED OFF' : data); } catch (_) {}
};
window.agentTraceStructurerWorkbarCopySmoke = (data) => {
  try { console.log('[workbar copy smoke]', data?.gated_off ? 'GATED OFF' : data); } catch (_) {}
};
window.agentTraceStructurerNativeError = (data) => {
  try { console.error('[native handler error]', data); } catch (_) {}
  try { setMissionBarStatus(`Native handler error: ${data?.handler || 'unknown'}`); } catch (_) {}
};
window.agentTraceStructurerRealClickSmoke = (data) => {
  try { console.log('[real-click smoke]', data?.gated_off ? 'GATED OFF' : (data?.smoke?.ok ? 'PASS' : 'FAIL'), data); } catch (_) {}
};

// v12 boot probe: mark module fully initialized + write final receipt
// with visible summary text so the operator can see exactly what the
// app populated (or didn't).
try {
  if (window.__aiwBoot) {
    window.__aiwBoot.script_finished = true;
    window.__aiwBoot.script_finished_at = new Date().toISOString();
    window.__aiwBoot.module_loaded = true;
    window.__aiwBoot.latest_clip_text = document.getElementById('latest-clip-summary')?.innerText || '';
    window.__aiwBoot.agent_trace_text = document.getElementById('agent-trace-summary')?.innerText || '';
    window.__aiwBoot.resource_freshness = window.__aiwResourceFreshness || null;
    window.__aiwBoot.body_resource_freshness = document.body.dataset.resourceFreshness || '';
    window.__aiwBoot.has_native_bridge = !!(window.webkit && window.webkit.messageHandlers);
    if (window.__aiwBootPost) window.__aiwBootPost('script_finished');
  }
} catch (_) {}
