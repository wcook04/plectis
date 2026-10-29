// The searchable, filterable component list, used by the map's Index view
// and the Catalogue page. It follows the brief's loading rules: blank search
// is omitted, superseded searches are aborted and refused, a cursor travels
// with its unchanged query, pages append only within one revision, and a
// stale cursor restarts the list once before asking the reader to retry.

import { ApiError, Collection, apiPath, getEnvelope, latestOnly, withQuery } from '../api.js';
import { backingGlyph, clear, h } from '../dom.js';
import { BACKING_OF, classWords, count, familyName, setLabels } from '../evidence.js';

export const FACETS = ['family', 'evidence_class', 'truth_accounting_bucket', 'real_substrate_disposition'];
export const FACET_TITLES = {
  family: 'Family',
  evidence_class: 'Kind of component',
  truth_accounting_bucket: 'Kind of saved result',
  real_substrate_disposition: 'Where its code comes from',
};

/** Read q and facet filters from a URL's query string. */
export function readQuery(url) {
  const out = { q: (url.searchParams.get('q') || '').slice(0, 160) };
  for (const f of FACETS) out[f] = url.searchParams.get(f) || '';
  return out;
}

/** Write them back, omitting blanks, keeping any other parameters. */
export function writeQuery(url, state) {
  const next = new URL(url.href);
  for (const key of ['q', ...FACETS]) {
    const v = (state[key] || '').trim();
    if (v) next.searchParams.set(key, v); else next.searchParams.delete(key);
  }
  return next;
}

export function filterSentence(state) {
  const parts = [];
  if (state.q && state.q.trim()) parts.push(`matching “${state.q.trim()}”`);
  for (const f of FACETS) if (state[f]) parts.push(`${FACET_TITLES[f].toLowerCase()}: ${classWords(f, state[f])}`);
  return parts.join('; ');
}

export function apiParams(state) {
  const params = {};
  if (state.q && state.q.trim()) params.q = state.q.trim();
  for (const f of FACETS) if (state[f]) params[f] = state[f];
  return params;
}

export function componentRow(item, { href, onEnter, onLeave, onPick } = {}) {
  const backing = BACKING_OF[item.classification?.evidence_class || item.evidence_class] || 'unknown';
  const formal = (item.formal_subclaim_ids || []).length > 0;
  const inner = [
    backingGlyph(backing, formal ? 'mark--proved' : 'mark'),
    h('span', { class: 'row__title' }, item.title || item.organ_id),
    h('span', { class: 'row__sub' }, `${item.classification?.family ? familyName(item.classification.family) : ''}. ${item.summary || ''}`),
  ];
  const el = onPick
    ? h('button', { type: 'button', class: 'row__go', onclick: () => onPick(item) }, inner)
    : h('a', { href, 'data-route': '' }, inner);
  if (onEnter) el.addEventListener('pointerenter', () => onEnter(item));
  if (onLeave) el.addEventListener('pointerleave', () => onLeave(item));
  if (onEnter) el.addEventListener('focus', () => onEnter(item));
  if (onLeave) el.addEventListener('blur', () => onLeave(item));
  return h('li', { class: 'row' }, el);
}

/**
 * Renders into `host` and returns { load(state), destroy() }. `onMatches`
 * receives every matching ID (fetched separately, all pages) so the map
 * can light them; `row` builds one list row.
 */
export function createCatalogue(host, { pageSize = 25, row, onMatches, onReset } = {}) {
  const run = latestOnly();
  const matchRun = latestOnly();
  let list = null;
  let state = {};
  let restarted = false;
  const status = h('p', { class: 'small muted figures', role: 'status', 'aria-live': 'polite' });
  const items = h('ul', { class: 'rows', 'aria-label': 'Components' });
  const actions = h('div', { class: 'more' });
  host.append(status, items, actions);

  function showError(error, retry) {
    clear(actions);
    const box = h('div', { class: 'state state--error', role: 'alert' });
    if (error.kind === 'request') {
      box.append(h('strong', {}, 'The API could not use this search. '), error.message, ' ');
      if (onReset) box.append(h('button', { type: 'button', class: 'textbtn', onclick: onReset }, 'Reset search and filters'));
    } else if (error.kind === 'schema') {
      box.append(h('strong', {}, 'This API speaks a different contract. '), error.message);
    } else if (error.kind === 'network') {
      box.append(h('strong', {}, 'The component API is not reachable. '), 'Start it with ', h('code', {}, 'plectis serve-components'), ' and try again. ');
      box.append(h('button', { type: 'button', class: 'textbtn', onclick: retry }, 'Try again'));
    } else {
      box.append(h('strong', {}, 'The list could not be loaded. '), error.message, ' ', h('button', { type: 'button', class: 'textbtn', onclick: retry }, 'Try again'));
    }
    if (list && list.items.length) box.append(h('p', { class: 'note' }, 'The rows below were loaded before this failure and may be out of date.'));
    actions.append(box);
  }

  function render() {
    clear(items);
    for (const item of list.items) items.append(row(item));
    const shown = list.items.length;
    status.textContent = list.total === 0
      ? 'No component matches.'
      : `${count(list.total, 'component')} ${list.total === 1 ? 'matches' : 'match'}; showing ${shown}.`;
    clear(actions);
    if (list.nextCursor) {
      actions.append(h('button', { type: 'button', class: 'btn', onclick: more }, `Show ${Math.min(pageSize, list.total - shown)} more`));
    }
    if (list.total === 0 && onReset) {
      actions.append(h('div', { class: 'state' }, 'Nothing in this snapshot matches. ', h('button', { type: 'button', class: 'textbtn', onclick: onReset }, 'Reset search and filters')));
    }
  }

  async function load(next) {
    state = next;
    restarted = false;
    list = new Collection(apiPath('components'), apiParams(state), { pageSize });
    status.textContent = 'Loading…';
    host.setAttribute('aria-busy', 'true');
    loadMatches();
    try {
      await run((signal) => list.first(signal));
      render();
    } catch (error) {
      if (error.kind === 'aborted') return;
      clear(items);
      status.textContent = '';
      showError(error, () => load(state));
    } finally {
      host.removeAttribute('aria-busy');
    }
  }

  async function more() {
    try {
      await run((signal) => list.more(signal));
      render();
    } catch (error) {
      if (error.kind === 'aborted') return;
      if ((error.kind === 'stale_cursor' || error.kind === 'revision') && !restarted) {
        // The snapshot changed: discard the list and start once from page one.
        const keep = state;
        await load(keep);
        restarted = true;
        actions.prepend(h('p', { class: 'note' }, 'The component index changed, so the list started again from the first page.'));
        return;
      }
      showError(error, more);
    }
  }

  async function loadMatches() {
    if (!onMatches) return;
    const params = apiParams(state);
    if (!Object.keys(params).length) { onMatches(null); return; }
    try {
      const ids = await matchRun(async (signal) => {
        const out = [];
        let cursor = null;
        let revision = '';
        do {
          const env = await getEnvelope(withQuery(apiPath('components'), { ...params, limit: 100, cursor }), { signal });
          if (revision && env.revision !== revision) throw new ApiError('revision', 'index changed');
          revision = env.revision;
          out.push(...env.data.items.map((c) => c.organ_id));
          cursor = env.data.next_cursor;
        } while (cursor);
        return out;
      });
      onMatches(new Set(ids));
    } catch (error) {
      if (error.kind !== 'aborted') onMatches(null);
    }
  }

  return { load, destroy() { host.replaceChildren(); } };
}

/** Metadata's advertised filter values with their counts. */
export async function loadFacets() {
  const env = await getEnvelope('/api/v1');
  setLabels(env.data.component_filters);
  return { revision: env.revision, filters: env.data.component_filters || {}, meta: env.data };
}
