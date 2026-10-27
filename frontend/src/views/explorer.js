// The evidence map page: the reading panel on the left, the drawing in the
// rest of the window (the universe map's explorer layout). The panel reads
// the map in levels: the families at rest, an index of every component, the
// filters, a key, and the card for whatever is chosen. A chosen object is
// addressable as #o=<key>; search and filters live in the query string.

import { apiPath, getEnvelope, loadTogether, withQuery } from '../api.js';
import { loadOverview } from '../data.js';
import { announce, backingGlyph, clear, copyButton, h, keyGlyph } from '../dom.js';
import {
  BACKING_ORDER, BACKING_WORDS, FAMILY_NAME, FAMILY_ORDER, availabilityWords, classWords, count, lastRunWords, proofShortName, stateWords,
} from '../evidence.js';
import { wireExplorer } from '../frame.js';
import { createMap } from '../map/engine.js';
import { FACETS, FACET_TITLES, componentRow, createCatalogue, filterSentence, loadFacets, readQuery, writeQuery } from './catalogue-core.js';

let cachedModel = null;
let revealPlayed = false;

export async function mountExplorer(root, { url, navigate }) {
  const canvas = h('canvas', { tabindex: '0', role: 'img', 'aria-label': 'Evidence map of the Plectis components. The panel lists everything the map draws.' });
  const status = h('div', { class: 'explorer__status', role: 'status' }, 'Reading the component index…');
  const legend = h('div', { class: 'explorer__legend', 'aria-label': 'Key' },
    h('span', { class: 'key' }, backingGlyph('tool', 'mark--proved'), 'Modeled contract, proof retained'),
    BACKING_ORDER.map((b) => h('span', { class: 'key' }, backingGlyph(b, 'mark'), BACKING_WORDS[b])),
    h('span', { class: 'key' }, keyGlyph('record'), 'Saved record'),
    h('span', { class: 'key' }, keyGlyph('absent'), 'Not in this snapshot'));
  const tools = h('div', { class: 'explorer__tools' },
    h('button', { type: 'button', class: 'explorer-tool', 'data-explorer-panel-toggle': '' }, h('span', { 'data-explorer-panel-label': '' }, 'Hide panel')),
    h('button', { type: 'button', class: 'explorer-tool', 'data-explorer-fit': '' }, 'Fit'),
    h('span', { class: 'explorer__zoom' },
      h('button', { type: 'button', class: 'explorer-tool explorer-tool--icon', 'data-explorer-zoom': 'out', 'aria-label': 'Zoom out' }, '−'),
      h('button', { type: 'button', class: 'explorer-tool explorer-tool--icon', 'data-explorer-zoom': 'in', 'aria-label': 'Zoom in' }, '+')),
    h('button', { type: 'button', class: 'explorer-tool', 'data-explorer-fullscreen': '' }, h('span', { 'data-explorer-fullscreen-label': '' }, 'Full screen')));
  const stage = h('div', { class: 'explorer__stage' }, canvas, tools, legend, status);

  const state = readQuery(url);
  const search = h('input', { type: 'search', id: 'map-find', placeholder: 'Find a component by name, ID or summary…', value: state.q, maxlength: '160', autocomplete: 'off', spellcheck: 'false' });
  const tabFamilies = h('button', { type: 'button', class: 'tab', 'aria-pressed': 'true' }, 'Families');
  const tabIndex = h('button', { type: 'button', class: 'tab', 'aria-pressed': 'false' }, 'Index');
  const utilFilters = h('button', { type: 'button', class: 'util', 'aria-pressed': 'false' }, 'Filters');
  const utilKey = h('button', { type: 'button', class: 'util', 'aria-pressed': 'false' }, 'How to read');
  const filteredText = h('span', {});
  const filtered = h('div', { class: 'filtered', hidden: true }, filteredText, h('button', { type: 'button', class: 'textbtn', onclick: () => resetQuery() }, 'Reset'));
  const lede = h('p', { class: 'panel-lede' }, 'Every component in the index, with the twelve whose selected computation has a Dafny-verified contract joined to the centre.');
  const body = h('div', { class: 'explorer__body', tabindex: '-1' });
  const foot = h('div', { class: 'explorer__foot figures' }, 'Index revision loading…');
  const panel = h('aside', { class: 'explorer__panel', 'aria-label': 'Reading the map' },
    h('div', { class: 'explorer__head' },
      h('h1', { class: 'explorer__title' }, 'The evidence map'),
      lede,
      h('div', { class: 'find' }, h('label', { class: 'sr-only', for: 'map-find' }, 'Find a component'), search),
      h('div', { class: 'tabs' },
        h('div', { class: 'tabs__group', role: 'group', 'aria-label': 'Read the map by' }, tabFamilies, tabIndex),
        h('div', { class: 'tabs__group', role: 'group', 'aria-label': 'Map tools' }, utilFilters, utilKey)),
      filtered),
    body, foot);
  const views = h('div', { class: 'explorer__views', role: 'group', 'aria-label': 'Show' },
    h('button', { type: 'button', class: 'explorer-tool', 'data-explorer-view': 'map', 'aria-pressed': 'true' }, 'Map'),
    h('button', { type: 'button', class: 'explorer-tool', 'data-explorer-view': 'details', 'aria-pressed': 'false' }, 'Details'));
  const explorer = h('div', { class: 'explorer', 'data-explorer': 'components' }, views, panel, stage);
  root.append(explorer);
  const unwire = wireExplorer(explorer);

  let map = null;
  let model = null;
  let panelView = 'families';
  let destroyed = false;
  let cardRun = 0;
  let currentMatches = null;
  const indexHost = h('div', {});
  const catalogue = createCatalogue(indexHost, {
    row: (item) => componentRow(item, {
      onPick: (it) => map && map.select(`comp:${it.organ_id}`),
      onEnter: (it) => map && map.hoverKey(`comp:${it.organ_id}`),
      onLeave: () => map && map.hoverKey(null),
    }),
    onMatches: (set) => { currentMatches = set; if (map) map.setMatches(set); },
    onReset: () => resetQuery(),
  });

  /* ---- Query state ------------------------------------------------------ */
  function syncFiltered() {
    const sentence = filterSentence(state);
    filtered.hidden = !sentence;
    filteredText.textContent = sentence ? `Showing components ${sentence}.` : '';
  }
  function commitQuery() {
    const next = writeQuery(new URL(window.location.href), state);
    history.replaceState(null, '', next.href);
    syncFiltered();
    catalogue.load(state);
  }
  function resetQuery() {
    state.q = '';
    for (const f of FACETS) state[f] = '';
    search.value = '';
    commitQuery();
    if (panelView === 'filters') showView('filters');
  }
  let debounce = 0;
  search.addEventListener('input', () => {
    clearTimeout(debounce);
    debounce = setTimeout(() => {
      state.q = search.value;
      commitQuery();
      if (search.value.trim() && panelView !== 'index') showView('index');
    }, 220);
  });
  search.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && search.value) { e.preventDefault(); search.value = ''; state.q = ''; commitQuery(); }
  });
  document.addEventListener('keydown', slashFocus);
  function slashFocus(e) {
    if (e.key === '/' && !(e.target instanceof HTMLInputElement) && !(e.target instanceof HTMLTextAreaElement)) {
      e.preventDefault(); search.focus();
    }
  }

  /* ---- Panel views -------------------------------------------------------- */
  function press(btn, on) { btn.setAttribute('aria-pressed', on ? 'true' : 'false'); }
  function showView(which) {
    panelView = which;
    press(tabFamilies, which === 'families');
    press(tabIndex, which === 'index');
    press(utilFilters, which === 'filters');
    press(utilKey, which === 'key');
    clear(body);
    if (which === 'families') body.append(familiesView());
    if (which === 'index') body.append(h('h2', { class: 'section-title' }, 'Every component, as a list'), indexHost);
    if (which === 'filters') body.append(filtersView());
    if (which === 'key') body.append(keyView());
    body.scrollTop = 0;
  }
  tabFamilies.addEventListener('click', () => { map?.select(null, { camera: false }); showView('families'); });
  tabIndex.addEventListener('click', () => { map?.select(null, { camera: false }); showView('index'); });
  utilFilters.addEventListener('click', () => { map?.select(null, { camera: false }); showView(panelView === 'filters' ? 'families' : 'filters'); });
  utilKey.addEventListener('click', () => { map?.select(null, { camera: false }); showView(panelView === 'key' ? 'families' : 'key'); });

  function familiesView() {
    if (!model) return h('p', { class: 'muted' }, 'Loading the families…');
    const t = model.totals;
    const rows = h('ul', { class: 'family-rows' });
    const families = [...new Set(model.components.map((c) => c.family))];
    const rank = (f) => (FAMILY_ORDER.includes(f) ? FAMILY_ORDER.indexOf(f) : FAMILY_ORDER.length);
    families.sort((a, b) => rank(a) - rank(b));
    for (const fam of families) {
      const members = model.components.filter((c) => c.family === fam).sort((a, b) => BACKING_ORDER.indexOf(a.backing) - BACKING_ORDER.indexOf(b.backing));
      const formal = members.filter((c) => c.kernelId).length;
      rows.append(h('li', { class: 'family-row' }, h('button', {
        type: 'button',
        onclick: () => { state.family = state.family === fam ? '' : fam; commitQuery(); showView('index'); },
        onpointerenter: () => map?.setMatches(new Set(members.map((c) => c.id))),
        onpointerleave: () => map?.setMatches(currentMatches),
      },
      h('span', { class: 'family-row__name' }, FAMILY_NAME[fam] || classWords('family', fam)),
      h('span', { class: 'family-row__count' }, String(members.length)),
      h('span', { class: 'family-row__tally' }, formal ? `${formal} with a verified kernel` : 'No verified kernel'),
      h('span', { class: 'family-row__marks', 'aria-hidden': 'true' }, members.map((c) => backingGlyph(c.backing, c.kernelId ? 'mark--proved' : 'mark'))))));
    }
    return h('div', {},
      h('p', { class: 'small' }, h('strong', {}, `${count(t.components, 'component')} in ${count(families.length, 'family', 'families')}. `),
        `${t.linkedKernels} have a selected computation with a modeled contract, verified by Dafny in the retained record (${t.tasks} tasks). `,
        `${count(t.receipts, 'saved record')} are listed; ${t.unavailable} of them are not in this snapshot. Whole-claim coverage is unknown for every component.`),
      h('h2', { class: 'section-title' }, 'The seven families'),
      rows,
      h('p', { class: 'note' }, 'Point at a family to light its components; choose it to list them. Choose a mark on the map, or a row, to read what its evidence establishes.'));
  }

  let facetData = null;
  function filtersView() {
    const wrap = h('div', {}, h('h2', { class: 'section-title' }, 'Filters'),
      h('p', { class: 'small muted' }, 'Each filter takes one value; filters combine with each other and with the search. Counts are for the whole index.'));
    if (!facetData) { wrap.append(h('p', { class: 'muted' }, 'Loading the filter values…')); return wrap; }
    for (const f of FACETS) {
      const values = facetData.filters[f] || [];
      if (!values.length) continue;
      const group = h('div', { class: 'facet', role: 'group', 'aria-label': FACET_TITLES[f] }, h('h3', {}, FACET_TITLES[f]));
      const choices = h('div', { class: 'facet__choices' });
      for (const v of values) {
        choices.append(h('button', {
          type: 'button', class: 'chip', 'aria-pressed': state[f] === v.value ? 'true' : 'false',
          onclick: () => { state[f] = state[f] === v.value ? '' : v.value; commitQuery(); showView('filters'); },
        }, f === 'evidence_class' ? backingGlyph({ external_subprocess_witness: 'tool', bounded_runtime_computation: 'bounded', verified_macro_body_import: 'import', semantic_validator: 'contract', algorithmic_projection: 'computes' }[v.value]) : null,
        classWords(f, v.value), h('span', { class: 'chip__n' }, String(v.component_count))));
      }
      group.append(choices);
      wrap.append(group);
    }
    wrap.append(h('div', { class: 'actions' }, h('button', { type: 'button', class: 'btn', onclick: () => showView('index') }, 'Show the matching list')));
    return wrap;
  }

  function keyView() {
    const item = (glyph, title, text) => h('li', { class: 'fact' }, glyph, h('span', {}, h('strong', {}, title), ' ', text));
    return h('div', {},
      h('h2', { class: 'section-title' }, 'How to read the map'),
      h('p', { class: 'small' }, 'The map follows one chain from the centre outward: a property is specified, Dafny verifies the computation against it, the computation is compiled to Python, an application caller runs that code, and a run saves a record. Red marks what a machine ran; azure marks what is stated.'),
      h('ul', { class: 'facts' },
        item(keyGlyph('kernel'), 'Kernel.', 'A modeled specification (azure ring) whose computation Dafny verified (red point). It covers a selected computation, not the whole component.'),
        item(keyGlyph('task'), 'Petals.', 'One for each verification task in the retained record. They are recorded results, not a run in this view.'),
        item(keyGlyph('variant'), 'Crosses.', 'Deliberately broken variants of the computation that the verifier rejected, in the retained record.'),
        item(keyGlyph('thread'), 'Thread.', 'From a kernel to the component whose code calls its generated implementation.'),
        item(keyGlyph('generated'), 'Square.', 'The generated Python, matched to its recorded hash when the index was built.'),
        item(keyGlyph('caller'), 'Diamond.', 'The application caller that runs the generated code.'),
        BACKING_ORDER.map((b) => item(backingGlyph(b, 'mark'), `${BACKING_WORDS[b]}.`, 'How the component is backed, in the system map\'s marks.')),
        item(backingGlyph('tool', 'mark--proved'), 'Red mark.', 'The component has a selected computation with a modeled contract and a retained proof.'),
        item(keyGlyph('record'), 'Dots outward.', 'Its saved run records; the first, larger dot is the record its claim cites.'),
        item(keyGlyph('absent'), 'Broken ring.', 'A record the index lists but this snapshot does not include. It is never drawn as a link.'),
        item(keyGlyph('wiring'), 'Azure curves.', 'Shown for a chosen component: wiring declared in source between components. It is untyped and is not a run.')),
      h('p', { class: 'note' }, 'The map has no score and no "verified component" mark. The core\'s right-hand satellite is hollow because this view records no fresh prover run.'));
  }

  /* ---- Cards for a chosen object -------------------------------------------- */
  function back() {
    return h('button', { type: 'button', class: 'textbtn', onclick: () => { map.select(null); } }, '← Back to the families');
  }
  function fact(facet, status, glyph) {
    const [text, caution, known] = stateWords(facet, status);
    return h('li', { class: `fact${known ? '' : ' fact--unknown'}` }, glyph || keyGlyph('record'),
      h('span', {}, h('span', { class: 'fact__text' }, text), caution ? h('span', { class: 'fact__caution' }, caution) : null));
  }
  async function componentCard(o) {
    const c = o.comp;
    const mine = ++cardRun;
    const card = h('div', {}, back(),
      h('p', { class: 'card-kind', style: 'margin-top:0.9rem' }, backingGlyph(c.backing, c.kernelId ? 'mark--proved' : 'mark'), `${BACKING_WORDS[c.backing] || classWords('evidence_class', c.evidenceClass)}. ${FAMILY_NAME[c.family] || c.family}.`),
      h('h2', { class: 'card-title' }, c.title),
      h('p', { class: 'card-summary' }, c.summary));
    clear(body).append(card);
    body.scrollTop = 0;
    let detail;
    try {
      const { parts } = await loadTogether([apiPath('components', c.id)]);
      [detail] = parts;
    } catch (error) {
      if (mine !== cardRun) return;
      card.append(h('div', { class: 'state state--error', role: 'alert' }, `The component's record could not be loaded: ${error.message}`));
      return;
    }
    if (mine !== cardRun || destroyed) return;
    const claim = detail.claim || {};
    const facets = claim.card?.assurance_facets || {};
    card.append(h('div', { class: 'limit' }, h('span', { class: 'limit__label' }, 'Where its claim stops'), claim.claim_ceiling_restated || claim.claim_ceiling || 'No limit is recorded.'));
    const facts = h('ul', { class: 'facts' },
      fact('formal_contract', facets.formal_contract?.status, c.kernelId ? keyGlyph('kernel') : keyGlyph('absent')),
      fact('whole_claim', facets.whole_claim?.status, keyGlyph('absent')));
    if (c.kernelId) {
      facts.append(fact('generated_runtime_binding', facets.generated_runtime_binding?.status, keyGlyph('generated')),
        fact('host_tests', facets.host_tests?.status, keyGlyph('caller')),
        fact('mutation_controls', facets.mutation_controls?.status, keyGlyph('variant')));
    }
    facts.append(fact('replay', facets.replay?.status, keyGlyph('record')),
      h('li', { class: 'fact' }, keyGlyph('record'), h('span', {}, lastRunWords(facets.replay?.last_result))),
      fact('requirements_review', facets.requirements_review?.status, keyGlyph('absent')),
      fact('fresh_prover', detail.evidence_state?.fresh_prover?.status, keyGlyph('absent')),
      fact('current_backend_binding', detail.evidence_state?.current_backend_binding?.status, keyGlyph('absent')));
    card.append(h('h3', { class: 'section-title' }, 'What its evidence establishes'), facts);
    if (c.kernelId) {
      const k = model.kernelById.get(c.kernelId);
      card.append(h('h3', { class: 'section-title' }, `Modeled contract: ${proofShortName(k)}`),
        h('p', { class: 'statement' }, k.statement),
        h('p', { class: 'small muted' }, `${count(k.verifiedTasks || 0, 'task')} verified and ${count(k.mutants.length, 'broken variant')} rejected in the retained record.`),
        h('div', { class: 'actions' }, h('a', { class: 'btn', href: `/proofs/${encodeURIComponent(k.id)}`, 'data-route': '' }, 'Read the proof')));
    }
    const records = h('ul', { class: 'ref-list' });
    for (const r of c.receipts) {
      const [words, available] = availabilityWords(r);
      records.append(h('li', {}, h('span', { class: available ? 'ref' : 'ref absent' }, r.ref), h('br'), h('span', { class: 'muted' }, words)));
    }
    card.append(h('h3', { class: 'section-title' }, `Saved records (${c.receipts.length})`), records);
    const wired = (model.wires.filter(([a, b]) => a === c.id || b === c.id)).map(([a, b]) => (a === c.id ? b : a));
    if (wired.length) {
      const list = h('ul', { class: 'rows' });
      for (const id of wired) {
        const other = model.byId.get(id);
        list.append(h('li', { class: 'row' }, h('button', { type: 'button', class: 'row__go', onclick: () => map.select(`comp:${id}`) },
          backingGlyph(other.backing, other.kernelId ? 'mark--proved' : 'mark'), h('span', { class: 'row__title' }, other.title),
          h('span', { class: 'row__sub' }, FAMILY_NAME[other.family] || other.family))));
      }
      card.append(h('h3', { class: 'section-title' }, `Declared wiring (${wired.length})`),
        h('p', { class: 'note' }, 'Wiring stated in source between components; it is untyped and does not show a run.'), list);
    }
    const replayCmd = detail.replay?.primary_execution?.argv;
    if (Array.isArray(replayCmd) && replayCmd.length) {
      const text = replayCmd.join(' ');
      card.append(h('h3', { class: 'section-title' }, 'Declared replay'),
        h('p', { class: 'small muted' }, 'A command the index declares for this component. This page copies it and runs nothing.'),
        h('code', { class: 'cmd' }, text), copyButton(text));
    }
    card.append(h('div', { class: 'actions' },
      h('a', { class: 'btn btn--ink', href: `/components/${encodeURIComponent(c.id)}`, 'data-route': '' }, 'Open the component page'),
      h('a', { class: 'btn', href: withQuery('/graph', { type: 'organ', id: c.id }), 'data-route': '' }, 'Related records')));
  }

  function kernelCard(o) {
    const k = o.kernel;
    const comp = o.componentId ? model.byId.get(o.componentId) : null;
    clear(body).append(h('div', {}, back(),
      h('p', { class: 'card-kind', style: 'margin-top:0.9rem' }, keyGlyph('kernel'), 'Modeled contract and retained proof'),
      h('h2', { class: 'card-title' }, proofShortName(k)),
      h('p', { class: 'statement' }, k.statement),
      h('div', { class: 'limit' }, h('span', { class: 'limit__label' }, 'What the model leaves out'), k.limits || 'No limit is recorded.'),
      h('h3', { class: 'section-title' }, 'Input model'), h('p', { class: 'small' }, k.inputModel),
      h('h3', { class: 'section-title' }, 'Assumptions'), h('p', { class: 'small' }, k.assumptions),
      h('ul', { class: 'facts' },
        h('li', { class: 'fact' }, keyGlyph('task'), h('span', {}, `Dafny verified ${count(k.verifiedTasks || 0, 'task')} in the retained record.`, h('span', { class: 'fact__caution' }, 'A recorded result; this view runs no prover.'))),
        h('li', { class: 'fact' }, keyGlyph('variant'), h('span', {}, `${count(k.mutants.length, 'deliberately broken variant')} failed verification in the retained record.`)),
        fact('proof_binding', k.binding, keyGlyph('generated')),
        fact('fresh_prover', k.freshProver, keyGlyph('absent')),
        fact('requirements_review', k.requirementsReview, keyGlyph('absent'))),
      h('div', { class: 'actions' },
        h('a', { class: 'btn btn--ink', href: `/proofs/${encodeURIComponent(k.id)}`, 'data-route': '' }, 'Read the proof'),
        comp ? h('button', { type: 'button', class: 'btn', onclick: () => map.select(`comp:${comp.id}`) }, `Its component: ${comp.title}`) : null)));
    body.scrollTop = 0;
  }

  function coreCard(o) {
    const t = model.totals;
    const wrap = h('div', {}, back());
    if (o.type === 'core' || o.id === 'retained') {
      wrap.append(h('p', { class: 'card-kind', style: 'margin-top:0.9rem' }, keyGlyph('kernel'), o.type === 'core' ? 'The centre of the map' : 'Retained verification'),
        h('h2', { class: 'card-title' }, o.type === 'core' ? 'Formal contracts' : 'Retained proofs'),
        h('p', { class: 'card-summary' }, o.type === 'core'
          ? `${count(t.kernels, 'specification')} in Dafny, each modeling one selected computation inside one component. Each is joined to the component whose code calls its generated implementation.`
          : `The index retains Dafny's verification records: ${t.tasks} tasks across ${count(t.kernels, 'kernel')}, with ${t.mutants} deliberately broken variants rejected. These are recorded results, tied to the source hashes recorded when the index was built.`),
        h('div', { class: 'limit' }, h('span', { class: 'limit__label' }, 'What this does not establish'), 'That any whole component is proved, that the specifications state the intended behaviour (no requirements review is recorded), or that the prover ran during this view.'));
      const list = h('ul', { class: 'rows' });
      for (const k of model.kernels) {
        list.append(h('li', { class: 'row' }, h('button', { type: 'button', class: 'row__go', onclick: () => map.select(`kernel:${k.id}`) },
          keyGlyph('kernel'), h('span', { class: 'row__title' }, proofShortName(k)),
          h('span', { class: 'row__sub figures' }, `${count(k.verifiedTasks || 0, 'task')}, ${count(k.mutants.length, 'broken variant')}. ${k.componentId ? model.byId.get(k.componentId)?.title : 'No component linked'}`))));
      }
      wrap.append(h('h3', { class: 'section-title' }, 'The kernels'), list);
    } else {
      wrap.append(h('p', { class: 'card-kind', style: 'margin-top:0.9rem' }, keyGlyph('absent'), 'Not recorded'),
        h('h2', { class: 'card-title' }, 'Fresh prover run'),
        h('p', { class: 'card-summary' }, 'This view reads a retained snapshot. It runs no prover and no replay, and the API has no endpoint that would. So the satellite stays hollow: no fresh result is recorded, which is neither a failure nor a success.'),
        h('ul', { class: 'facts' }, fact('fresh_prover', model.meta?.evidence_state?.fresh_prover?.status, keyGlyph('absent')),
          fact('fresh_replay', model.meta?.evidence_state?.fresh_replay?.status, keyGlyph('absent')),
          fact('current_backend_binding', model.meta?.evidence_state?.current_backend_binding?.status, keyGlyph('absent'))));
    }
    clear(body).append(wrap);
    body.scrollTop = 0;
  }

  function onSelect(o) {
    const hash = o ? `#o=${encodeURIComponent(o.key)}` : '';
    history.replaceState(null, '', `${window.location.pathname}${window.location.search}${hash}`);
    if (!o) { showView(panelView === 'card' ? 'families' : panelView); return; }
    panelView = 'card';
    for (const b of [tabFamilies, tabIndex, utilFilters, utilKey]) press(b, false);
    explorer.dispatchEvent(new CustomEvent('explorer:selected', { bubbles: true }));
    if (o.type === 'component') { componentCard(o); announce(`${o.comp.title} selected`); }
    else if (o.type === 'kernel') { kernelCard(o); announce(`${proofShortName(o.kernel)} kernel selected`); }
    else coreCard(o);
  }

  /* ---- Boot ----------------------------------------------------------------- */
  showView(state.q ? 'index' : 'families');
  syncFiltered();
  const facetsLoad = loadFacets().then((f) => { facetData = f; if (panelView === 'filters') showView('filters'); }).catch(() => {});
  try {
    if (cachedModel) {
      const meta = await getEnvelope('/api/v1');
      if (meta.revision !== cachedModel.revision) cachedModel = null;
    }
    model = cachedModel || await loadOverview({
      onProgress: (n, total) => { status.textContent = `Reading the component index… ${n} of ${total} components`; },
    });
    cachedModel = model;
  } catch (error) {
    if (destroyed) return () => {};
    status.replaceChildren(errorBlock(error, () => navigate(window.location.href, { replace: true })));
    foot.textContent = '';
    return () => { destroyed = true; unwire(); document.removeEventListener('keydown', slashFocus); };
  }
  if (destroyed) return () => {};
  status.hidden = true;
  foot.textContent = `Index revision ${model.revision.slice(0, 12)}: a digest of the served index, not a Git commit or a proof.`;
  foot.title = model.revision;
  lede.textContent = `${count(model.totals.components, 'component')} in seven families. A thread joins each of the ${model.totals.linkedKernels} whose selected computation has a Dafny-verified contract to the centre; the rest stand on their saved records.`;
  if (revealPlayed) document.documentElement.classList.add('map-seen');
  map = createMap(canvas, model, {
    onSelect,
    onOpen: (o) => {
      if (o.type === 'component') navigate(`/components/${encodeURIComponent(o.id)}`);
      if (o.type === 'kernel') navigate(`/proofs/${encodeURIComponent(o.id)}`);
    },
    skipReveal: revealPlayed,
  });
  revealPlayed = true;
  explorer.addEventListener('explorer:fit', () => map.fit());
  explorer.addEventListener('explorer:zoom', (e) => map.zoomBy(e.detail.direction > 0 ? 1.4 : 1 / 1.4));
  explorer.addEventListener('explorer:resize', () => map.resize());
  catalogue.load(state);
  if (panelView === 'families') showView('families');
  const wanted = decodeURIComponent((window.location.hash.match(/^#o=(.+)$/) || [])[1] || '');
  if (wanted && map.objectFor(wanted)) map.select(wanted);
  await facetsLoad;

  return () => {
    destroyed = true;
    map?.destroy();
    unwire();
    catalogue.destroy();
    document.removeEventListener('keydown', slashFocus);
    document.documentElement.classList.remove('is-map-fullscreen');
  };
}

export function errorBlock(error, retry) {
  const box = h('div', { class: 'state state--error', role: 'alert', style: 'max-width:46ch;text-align:left' });
  if (error.kind === 'network') {
    box.append(h('strong', {}, 'The component API is not reachable. '), 'Start it from the repository with ', h('code', {}, 'PYTHONPATH=src python3 -m plectis serve-components'), ', or start this explorer with ', h('code', {}, 'python3 frontend/serve.py --start-backend'), '.');
  } else if (error.kind === 'schema') {
    box.append(h('strong', {}, 'The API answered with a contract this explorer does not read. '), error.message);
  } else if (error.kind === 'revision') {
    box.append(h('strong', {}, 'The component index changed twice while loading. '), 'Nothing from the two snapshots was combined.');
  } else {
    box.append(h('strong', {}, 'The map could not be loaded. '), error.message);
  }
  box.append(' ', h('button', { type: 'button', class: 'textbtn', onclick: retry }, 'Try again'));
  return box;
}
