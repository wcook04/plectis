// The catalogue page: search and combined filters, the matching total and
// further pages, all kept in the URL so a reload returns the same list.

import { h } from '../dom.js';
import { classWords } from '../evidence.js';
import { FACETS, FACET_TITLES, componentRow, createCatalogue, filterSentence, loadFacets, readQuery, writeQuery } from './catalogue-core.js';

export async function mountCatalogue(root, { url }) {
  const state = readQuery(url);
  const search = h('input', { type: 'search', id: 'cat-find', value: state.q, maxlength: '160', placeholder: 'Search component IDs, titles and summaries…', autocomplete: 'off', spellcheck: 'false' });
  const facetsHost = h('div', {}, h('p', { class: 'muted small' }, 'Loading the filters…'));
  const sentence = h('p', { class: 'small muted', 'aria-live': 'polite' });
  const listHost = h('div', {});
  const page = h('div', { class: 'page' },
    h('nav', { class: 'trail', 'aria-label': 'Breadcrumb' }, h('a', { href: '/', 'data-route': '' }, 'Map'), h('span', { 'aria-hidden': 'true' }, '/'), h('span', {}, 'Catalogue')),
    h('h1', { class: 'page-title' }, 'Components'),
    h('p', { class: 'page-lede' }, 'Every component in the system. Search by name or by words from its description, and narrow the list with the filters.'),
    h('div', { class: 'graph-layout' },
      h('div', {},
        h('div', { class: 'find', style: 'margin-top:0' }, h('label', { class: 'sr-only', for: 'cat-find' }, 'Search components'), search),
        sentence, listHost),
      h('aside', { 'aria-label': 'Filters' }, h('h2', { style: 'margin-top:0' }, 'Filters'), facetsHost)));
  root.append(page);

  const catalogue = createCatalogue(listHost, {
    row: (item) => componentRow(item, { href: `/components/${encodeURIComponent(item.organ_id)}` }),
    onReset: () => reset(),
  });
  let facets = null;
  function commit() {
    history.replaceState(null, '', writeQuery(new URL(window.location.href), state).href);
    const s = filterSentence(state);
    sentence.textContent = s ? `Showing components ${s}.` : 'Showing every component.';
    catalogue.load(state);
    renderFacets();
  }
  function reset() {
    state.q = ''; search.value = '';
    for (const f of FACETS) state[f] = '';
    commit();
  }
  function renderFacets() {
    if (!facets) return;
    facetsHost.replaceChildren();
    for (const f of FACETS) {
      const values = facets.filters[f] || [];
      if (!values.length) continue;
      const choices = h('div', { class: 'facet__choices' });
      for (const v of values) {
        choices.append(h('button', {
          type: 'button', class: 'chip', 'aria-pressed': state[f] === v.value ? 'true' : 'false',
          onclick: () => { state[f] = state[f] === v.value ? '' : v.value; commit(); },
        }, classWords(f, v.value), h('span', { class: 'chip__n' }, String(v.component_count))));
      }
      facetsHost.append(h('div', { class: 'facet', role: 'group', 'aria-label': FACET_TITLES[f] }, h('h3', {}, FACET_TITLES[f]), choices));
    }
    facetsHost.append(h('button', { type: 'button', class: 'btn', onclick: reset }, 'Reset search and filters'));
  }
  let debounce = 0;
  search.addEventListener('input', () => {
    clearTimeout(debounce);
    debounce = setTimeout(() => { state.q = search.value; commit(); }, 220);
  });
  loadFacets().then((f) => { facets = f; renderFacets(); }).catch(() => {
    facetsHost.replaceChildren(h('p', { class: 'state state--error' }, 'The filter values could not be loaded; search still works.'));
  });
  commit();
  return () => { clearTimeout(debounce); catalogue.destroy(); };
}
