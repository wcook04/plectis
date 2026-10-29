// The evidence map page: the reading panel on the left, the drawing in the
// rest of the window (the universe map's explorer layout). At rest the panel
// reads the map's coverage rings as strips, one per kind of check, then the
// families and the verified computations. A chosen object gets a card. A
// chosen object is addressable as #o=<key>; search and filters live in the
// query string.

import { ApiError, apiPath, getEnvelope, withQuery } from '../api.js';
import { getModel } from '../data.js';
import { announce, backingGlyph, clear, copyButton, dialGlyph, h, keyGlyph, ringStyle, ringSwatch, ruleGlyph, svg } from '../dom.js';
import {
  BACKING_ORDER, CITATION_WORDS, CLASS_OF_BACKING, DOCTRINE_KINDS, EXPOSURE_WORDS, FAMILY_ORDER, TRACKS, callerWords, classDescription, classWords, count, dayWords, familyName, moduleWords,
  obligationWords, proofShortName, ruleKindPlain, ruleKindWords, setLabels, sourceHref, stateWords, supportWords, CORE_NAMES, flowerWords, ordinal, ringState,
} from '../evidence.js';
import { loadWriteup, renderGuide, renderWriteup } from '../markdown.js';
import { wireExplorer } from '../frame.js';
import { createMap } from '../map/engine.js';
import { arrange } from '../map/layout.js';
import { FACETS, FACET_TITLES, componentRow, createCatalogue, filterSentence, readQuery, writeQuery } from './catalogue-core.js';
import { ownershipFigure, runsStrip, specificationParts, variantsPart } from './proofparts.js';
import { openExplainer } from './explain.js';
import { placement, preview, readout } from './readout.js';

let revealPlayed = false;

const INK_CLASS = { ran: 'ink-ran', stated: 'ink-stated', saved: 'ink-saved', unknown: 'ink-unknown' };

/** A small swatch in a ring's own colour: filled, empty, or hatched. */
const swatch = (track, state) => ringSwatch(track, state);

export async function mountExplorer(root, { url, navigate, signal }) {
  const canvas = h('canvas', { tabindex: '0', role: 'img', 'aria-label': 'Map of the Plectis components and their checks. The panel beside it gives the same information as text.' });
  const status = h('div', { class: 'explorer__status', role: 'status' }, 'Reading the component index…');
  const legend = h('div', { class: 'explorer__legend', 'aria-label': 'Key' },
    h('span', { class: 'key' }, keyGlyph('kernel'), 'Proved computation'),
    h('span', { class: 'key' }, keyGlyph('thread'), 'Calls proved code'),
    h('span', { class: 'key' }, keyGlyph('spoke'), 'Rerun path'),
    h('span', { class: 'key', title: 'A mark’s shape says how the component is backed' }, backingGlyph('computes', 'mark'), 'Component'),
    h('span', { class: 'key' }, h('span', { class: 'swatch is-empty', 'aria-hidden': 'true' }), 'Not recorded'),
    h('span', { class: 'key' }, h('span', { class: 'swatch ink-unknown', 'aria-hidden': 'true' }), 'Unknown'),
    h('span', { class: 'key key--rules', 'data-halo-key': '', title: 'Principle, axiom and failure mode' }, ruleGlyph('principle'), ruleGlyph('axiom'), ruleGlyph('anti_principle'), 'Rules'),
    h('span', { class: 'key', 'data-halo-key': '', title: 'A rule the component’s own record cites' }, keyGlyph('cites'), 'Citation'));
  const wiringBtn = h('button', { type: 'button', class: 'explorer-tool', 'aria-pressed': 'false', title: 'Show every declared connection between components' }, 'Wiring');
  const tools = h('div', { class: 'explorer__tools' },
    h('button', { type: 'button', class: 'explorer-tool', 'data-explorer-panel-toggle': '' }, h('span', { 'data-explorer-panel-label': '' }, 'Hide panel')),
    wiringBtn,
    h('button', { type: 'button', class: 'explorer-tool', 'data-explorer-fit': '' }, 'Fit'),
    h('span', { class: 'explorer__zoom' },
      h('button', { type: 'button', class: 'explorer-tool explorer-tool--icon', 'data-explorer-zoom': 'out', 'aria-label': 'Zoom out' }, '−'),
      h('button', { type: 'button', class: 'explorer-tool explorer-tool--icon', 'data-explorer-zoom': 'in', 'aria-label': 'Zoom in' }, '+')),
    h('button', { type: 'button', class: 'explorer-tool', 'data-explorer-fullscreen': '' }, h('span', { 'data-explorer-fullscreen-label': '' }, 'Full screen')));
  // The rings' key, as a slice of the map's top: the component at the
  // bottom and each ring stacked outward above it, numbered 01-08 from the
  // component, in its own ink, with how many of the components it fills.
  // Where the stage corner has no room it folds to a "Key" chip.
  const ringCounts = new Map();
  const ringKeyChip = h('button', { type: 'button', class: 'ringkey__chip', 'aria-expanded': 'false', 'aria-controls': 'ringkey-panel' }, 'Ring key');
  const ringKey = h('div', { class: 'explorer__rings' },
    ringKeyChip,
    h('div', { class: 'ringkey__panel', id: 'ringkey-panel' },
      // The map names each ring in the wedge; here each line says, in plain
      // words and on one line, what a filled cell in that ring means.
      h('p', { class: 'ringkey__title', id: 'ringkey-title' }, 'What a filled cell means', h('span', { class: 'ringkey__sub' }, 'from the component outward')),
      h('ol', { class: 'ringkey', 'aria-labelledby': 'ringkey-title', reversed: true },
        [...TRACKS].reverse().map((t) => {
          const n = h('span', { class: 'ringkey__n figures' });
          ringCounts.set(t.id, n);
          return h('li', {
            class: 'ringkey__row',
            title: `${t.title}: what it means`,
            onclick: () => openExplainer(t.id),
            onpointerenter: () => { if (!pinnedTrack) map?.emphasise(t.id); },
            onpointerleave: () => { if (!pinnedTrack) map?.emphasise(null); },
          }, h('span', { class: 'ringkey__no figures' }, ordinal(TRACKS.indexOf(t))), swatch(t, t.ink === 'unknown' ? 'unknown' : 'has'), h('span', { class: 'ringkey__name' }, t.lay || t.short), n);
        })),
      h('p', { class: 'ringkey__base' }, h('span', { class: 'ringkey__mark', 'aria-hidden': 'true' }), 'The component'),
      h('button', { type: 'button', class: 'ringkey__more', onclick: () => openExplainer() }, 'What do these mean?')));
  ringKeyChip.addEventListener('click', () => {
    const open = !ringKey.classList.contains('is-open');
    ringKey.classList.toggle('is-open', open);
    ringKeyChip.setAttribute('aria-expanded', String(open));
    ringKeyChip.textContent = open ? 'Close ring key' : 'Ring key';
  });
  const stage = h('div', { class: 'explorer__stage' }, canvas, ringKey, tools, legend, status);

  const state = readQuery(url);
  const search = h('input', { type: 'search', id: 'map-find', placeholder: 'Search the components…', value: state.q, maxlength: '160', autocomplete: 'off', spellcheck: 'false' });
  const tabOverview = h('button', { type: 'button', class: 'tab', 'aria-pressed': 'true' }, 'Overview');
  const tabIndex = h('button', { type: 'button', class: 'tab', 'aria-pressed': 'false' }, 'Components');
  const tabDoctrine = h('button', { type: 'button', class: 'tab', 'aria-pressed': 'false' }, 'Rules');
  const utilFilters = h('button', { type: 'button', class: 'util', 'aria-pressed': 'false' }, 'Filters');
  const utilKey = h('button', { type: 'button', class: 'util', 'aria-pressed': 'false' }, 'Key');
  const filteredText = h('span', {});
  const filtered = h('div', { class: 'filtered', hidden: true }, filteredText, h('button', { type: 'button', class: 'textbtn', onclick: () => resetQuery() }, 'Reset'));
  const body = h('div', { class: 'explorer__body', tabindex: '-1' });
  const foot = h('div', { class: 'explorer__foot figures' }, 'Loading…');
  // The preview dock: the object under the pointer, said against the chosen
  // one, at the foot of the panel so it never covers the drawing.
  const dock = h('section', { class: 'dock', 'aria-label': 'Preview of the object under the pointer' });
  // The page's name, for assistive tech, whenever the overview (which shows
  // it as its heading) is not in the panel.
  const srTitle = h('h1', { class: 'sr-only' }, 'What’s proved, and what isn’t');
  const panel = h('aside', { class: 'explorer__panel', 'aria-label': 'Map details' },
    // A compact head: search, the three views and the key. The title lives
    // in the overview, which returns after Escape.
    h('div', { class: 'explorer__head explorer__head--compact' },
      h('div', { class: 'find' }, h('label', { class: 'sr-only', for: 'map-find' }, 'Find a component'), search),
      h('div', { class: 'tabs' },
        h('div', { class: 'tabs__group', role: 'group', 'aria-label': 'Panel view' }, tabOverview, tabIndex, tabDoctrine),
        h('div', { class: 'tabs__group', role: 'group', 'aria-label': 'Map tools' }, utilFilters, utilKey)),
      filtered),
    h('div', { class: 'sheetbar' },
      h('button', { type: 'button', class: 'explorer-tool', 'data-explorer-sheet-toggle': '', 'aria-expanded': 'false' }, 'Read more'),
      h('button', { type: 'button', class: 'explorer-tool', onclick: () => map?.select(null) }, 'Close')),
    body, dock, foot);
  const views = h('div', { class: 'explorer__views', role: 'group', 'aria-label': 'Show' },
    h('button', { type: 'button', class: 'explorer-tool', 'data-explorer-view': 'map', 'aria-pressed': 'true' }, 'Map'),
    h('button', { type: 'button', class: 'explorer-tool', 'data-explorer-view': 'details', 'aria-pressed': 'false' }, 'Details'));
  const explorer = h('div', { class: 'explorer', 'data-explorer': 'components' }, views, panel, stage);
  root.append(explorer);
  const unwire = wireExplorer(explorer);

  let map = null;
  let model = null;
  let panelView = 'overview';
  // The view a card was opened from, so letting go returns there.
  let cameFrom = 'overview';
  const VIEW_TITLES = { overview: 'the overview', index: 'all components', doctrine: 'the rules', filters: 'the filters' };
  const VIEW_SHORT = { overview: 'Overview', index: 'Components', doctrine: 'Rules', filters: 'Filters' };
  let destroyed = false;
  let peekTimer = 0, peekKey = null, dismissedKey = null, indexHeading = null;
  let cardRun = 0;
  let currentMatches = null;
  let catalogueLoaded = false;
  let pinnedTrack = null;
  const indexHost = h('div', {});
  const catalogue = createCatalogue(indexHost, {
    row: (item) => componentRow(item, {
      onPick: (it) => map && map.select(`comp:${it.organ_id}`),
      onEnter: (it) => map && map.hoverKey(`comp:${it.organ_id}`),
      onLeave: () => map && map.hoverKey(null),
    }),
    onMatches: (set, error) => {
      currentMatches = set;
      syncIndexHeading();
      if (map && !pinnedTrack) map.setMatches(set);
      if (error?.kind === 'revision') foot.textContent = 'The index changed. Reload the map to apply this search.';
    },
    expectedRevision: () => model?.revision || '',
    onReset: () => resetQuery(),
  });

  wiringBtn.addEventListener('click', () => {
    if (!map) return;
    const on = map.showWiring(wiringBtn.getAttribute('aria-pressed') !== 'true');
    wiringBtn.setAttribute('aria-pressed', String(on));
    announce(on ? `Showing all ${model.totals.wires} declared connections` : 'Connections hidden');
  });

  const dispose = () => {
    if (destroyed) return;
    destroyed = true;
    clearTimeout(debounce);
    clearTimeout(peekTimer);
    map?.destroy();
    unwire();
    catalogue.destroy();
    document.removeEventListener('keydown', slashFocus);
    document.removeEventListener('keydown', previewFirst, true);
    window.removeEventListener('resize', fitRingKey);
    document.documentElement.classList.remove('is-map-fullscreen');
  };

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
    catalogueLoaded = true;
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
  // The drawing lets go of its choice on Escape itself; a preview showing
  // goes first, so this listens before the canvas does.
  document.addEventListener('keydown', previewFirst, true);
  function previewFirst(e) {
    if (e.key !== 'Escape' || !dockShown() || document.querySelector('dialog[open]')) return;
    const typing = e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement;
    if (typing && e.target.value) return;
    e.preventDefault();
    e.stopPropagation();
    dismissPreview();
  }
  function slashFocus(e) {
    // An open window (the key) handles its own keys.
    if (document.querySelector('dialog[open]')) return;
    const typing = e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement;
    if (e.key === '/' && !typing) {
      e.preventDefault(); search.focus();
    }
    // Escape steps back one layer, wherever the focus is: first a preview,
    // then the chosen object, then a ring kept lit, then the overview.
    if (e.key === 'Escape' && !(typing && e.target.value) && !e.defaultPrevented) {
      if (dockShown()) { e.preventDefault(); dismissPreview(); }
      else if (map?.selectedKey()) { e.preventDefault(); map.select(null); }
      else if (pinnedTrack) {
        e.preventDefault();
        const row = body.querySelector('.ring-row.is-pinned');
        const track = TRACKS.find((x) => x.id === pinnedTrack);
        if (row && track) pinTrack(track, row); else { pinnedTrack = null; map?.emphasise(null); map?.setMatches(currentMatches); }
      } else if (panelView !== 'overview' && panelView !== 'card') {
        // Then back to the start, where the map is explained.
        e.preventDefault();
        showView('overview');
      }
    }
  }

  // "8 components match 'proof' · of 88", or every component.
  function syncIndexHeading() {
    if (!indexHeading) return;
    const total = model ? model.totals.components : '';
    const sentence = filterSentence(state);
    if (!sentence || !currentMatches) { indexHeading.textContent = sentence ? 'Searching the components…' : `All ${total} components`; return; }
    const n = currentMatches.size;
    const q = state.q.trim();
    indexHeading.textContent = `${count(n, 'component')} ${n === 1 ? 'matches' : 'match'} ${q ? `‘${q}’` : 'these filters'}${q && FACETS.some((f) => state[f]) ? ' and the filters' : ''} · of ${total}`;
  }

  /* ---- Panel views -------------------------------------------------------- */
  function press(btn, on) { btn.setAttribute('aria-pressed', on ? 'true' : 'false'); }
  function showView(which) {
    cardRun += 1;
    panelView = which;
    press(tabOverview, which === 'overview');
    press(tabIndex, which === 'index');
    press(tabDoctrine, which === 'doctrine');
    press(utilFilters, which === 'filters');
    press(utilKey, which === 'key');
    clear(body);
    if (which === 'overview') srTitle.remove(); else if (!srTitle.isConnected) panel.prepend(srTitle);
    if (which === 'overview') body.append(overviewView());
    if (which === 'index') {
      indexHeading = h('h2', { class: 'section-title search-count figures' });
      syncIndexHeading();
      body.append(indexHeading, indexHost);
      if (model && !catalogueLoaded) { catalogueLoaded = true; catalogue.load(state); }
    }
    if (which === 'doctrine') body.append(doctrineView());
    if (which === 'filters') body.append(filtersView());
    body.scrollTop = 0;
  }
  tabOverview.addEventListener('click', () => { map?.select(null, { camera: false }); showView('overview'); });
  tabIndex.addEventListener('click', () => { map?.select(null, { camera: false }); showView('index'); });
  tabDoctrine.addEventListener('click', () => { map?.select(null, { camera: false }); showView('doctrine'); });
  utilFilters.addEventListener('click', () => { map?.select(null, { camera: false }); showView(panelView === 'filters' ? 'overview' : 'filters'); });
  utilKey.addEventListener('click', () => openExplainer());

  // A ring unrolled: one cell per component, in the ring's order, families
  // apart. It is the same picture as the map's ring, read as a line.
  function strip(track, order) {
    const cell = 4, gap = 1, famGap = 4;
    let x = 0;
    const rects = [];
    order.forEach((group, gi) => {
      if (gi) x += famGap;
      for (const c of group) {
        const has = track.ink === 'unknown' ? 'unknown' : c.checks[track.id] ? 'has' : 'empty';
        rects.push(svg('rect', { x, y: 0, width: cell, height: 12, rx: 0.6, class: `cell cell--${has}` }));
        x += cell + gap;
      }
    });
    return svg('svg', { class: `strip ${INK_CLASS[track.ink]}`, style: ringStyle(track) || null, viewBox: `0 0 ${x - gap} 12`, preserveAspectRatio: 'none', 'aria-hidden': 'true', focusable: 'false' }, rects);
  }
  function ringOrder() {
    const { sectors } = arrange(model.components);
    return sectors.map((s) => s.members.map((id) => model.byId.get(id)));
  }
  function trackSet(track) {
    return new Set(model.components.filter((c) => (track.ink === 'unknown' ? true : c.checks[track.id])).map((c) => c.id));
  }
  function pinTrack(track, row) {
    const on = pinnedTrack !== track.id;
    pinnedTrack = on ? track.id : null;
    for (const r of body.querySelectorAll('.ring-row')) r.classList.toggle('is-pinned', on && r === row);
    for (const r of body.querySelectorAll('.ring-row__go')) r.setAttribute('aria-pressed', String(on && r.parentElement === row));
    map?.emphasise(pinnedTrack);
    map?.setMatches(on && track.ink !== 'unknown' ? trackSet(track) : currentMatches);
  }
  function overviewView() {
    if (!model) return h('p', { class: 'muted' }, 'Loading…');
    const t = model.totals;
    const order = ringOrder();
    const cov = model.coverage.component_presence || {};
    // The eight rings as the key: numbered from the component outward, each
    // with its swatch, how many components it fills and one line of meaning.
    const rows = h('ol', { class: 'rings ring-key' });
    TRACKS.forEach((track, i) => {
      const measure = track.measure ? cov[track.measure] : null;
      const n = track.ink === 'unknown' ? null : model.components.filter((c) => c.checks[track.id]).length;
      const row = h('li', { class: `ring-row${pinnedTrack === track.id ? ' is-pinned' : ''}` });
      row.append(h('button', {
        type: 'button', class: 'ring-row__go', 'aria-pressed': String(pinnedTrack === track.id),
        title: measure?.kind ? `Counted as: ${measure.kind}` : '',
        onclick: () => pinTrack(track, row),
        onpointerenter: () => { if (!pinnedTrack) map?.emphasise(track.id); },
        onpointerleave: () => { if (!pinnedTrack) map?.emphasise(null); },
        onfocus: () => { if (!pinnedTrack) map?.emphasise(track.id); },
        onblur: () => { if (!pinnedTrack) map?.emphasise(null); },
      },
      h('span', { class: 'ring-row__title' }, h('span', { class: 'ring-row__no figures' }, ordinal(i)), swatch(track, track.ink === 'unknown' ? 'unknown' : 'has'), track.short),
      h('span', { class: `ring-row__count figures${n === null ? ' is-unknown' : ''}` }, n === null ? 'unknown' : `${n}/${t.components}`),
      h('span', { class: 'ring-row__by' }, track.line),
      strip(track, order)));
      rows.append(row);
    });
    const families = [...new Set(model.components.map((c) => c.family))];
    const rank = (f) => (FAMILY_ORDER.includes(f) ? FAMILY_ORDER.indexOf(f) : FAMILY_ORDER.length);
    families.sort((a, b) => rank(a) - rank(b));
    const famRows = h('ul', { class: 'family-rows' });
    for (const fam of families) {
      const members = model.components.filter((c) => c.family === fam).sort((a, b) => BACKING_ORDER.indexOf(a.backing) - BACKING_ORDER.indexOf(b.backing));
      const formal = members.filter((c) => c.kernelId).length;
      famRows.append(h('li', { class: 'family-row' }, h('button', {
        type: 'button',
        title: classDescription('family', fam),
        onclick: () => { state.family = state.family === fam ? '' : fam; commitQuery(); showView('index'); },
        onpointerenter: () => map?.setMatches(new Set(members.map((c) => c.id))),
        onpointerleave: () => map?.setMatches(pinnedTrack ? trackSet(TRACKS.find((x) => x.id === pinnedTrack)) : currentMatches),
      },
      h('span', { class: 'family-row__name' }, familyName(fam)),
      h('span', { class: 'family-row__count figures' }, String(members.length)),
      h('span', { class: 'family-row__tally' }, formal ? `${formal} with a proved computation` : 'None with a proved computation'),
      h('span', { class: 'family-row__marks', 'aria-hidden': 'true' }, members.map((c) => backingGlyph(c.backing, c.kernelId ? 'mark--proved' : 'mark'))))));
    }
    const computations = h('ul', { class: 'rows' });
    for (const core of model.cores) {
      computations.append(h('li', { class: 'row' }, h('button', { type: 'button', class: 'row__go', onclick: () => map.select(`core:${core.id}`) },
        keyGlyph('kernel'), h('span', { class: 'row__title' }, CORE_NAMES[core.id]?.[0] || moduleWords(core.id)),
        h('span', { class: 'row__sub figures' }, `${core.id === 'replay_admission' ? 'At the centre · judges reruns' : 'Part of the toolkit'} · ${count(core.verifiedTasks || 0, 'proof check')} passed · ${count(core.mutants.length, 'broken copy', 'broken copies')} rejected`))));
    }
    for (const k of model.kernels) {
      computations.append(h('li', { class: 'row' }, h('button', { type: 'button', class: 'row__go', onclick: () => map.select(`kernel:${k.id}`) },
        keyGlyph('kernel'), h('span', { class: 'row__title' }, proofShortName(k)),
        h('span', { class: 'row__sub figures' }, `${count(k.verifiedTasks || 0, 'proof check')} passed · ${count(k.mutants.length, 'broken copy', 'broken copies')} rejected · in ${k.componentId ? model.byId.get(k.componentId)?.title : 'no component'}`))));
    }
    const example = model.byId.get('mcp_tool_authority_replay');
    return h('div', { class: 'overview' },
      h('h1', { class: 'explorer__title' }, 'What’s proved, and what isn’t'),
      h('p', { class: 'overview__lead' }, `Plectis is a toolkit of ${t.components} software mechanisms for AI research and engineering. Only the proof dials are proofs: small computations a prover checked. Everything else is recorded evidence. Nothing runs on this page.`),
      layersGuide(),
      h('div', { class: 'section-head' }, h('h2', { class: 'section-title' }, 'The eight rings'),
        h('button', { type: 'button', class: 'textbtn', onclick: () => openExplainer() }, 'What do these mean?')),
      h('p', { class: 'small muted' }, `Numbered from the component outward. Each cell is one component, in the map’s order; the count says how many of the ${t.components} have it. Hover over a row to highlight its ring on the map, or click to keep it highlighted.`),
      rows,
      h('p', { class: 'note' }, 'These are not a score. The rings overlap, their counts do not add up, and none of them means a whole component is proved.'),
      example ? h('section', { class: 'introduction', 'aria-label': 'Example' }, h('ul', { class: 'rows' }, h('li', { class: 'row' }, h('button', { type: 'button', class: 'row__go row__go--start', 'data-start-example': '', onclick: () => map?.select(`comp:${example.id}`) },
        backingGlyph(example.backing, example.kernelId ? 'mark--proved' : 'mark'),
        h('span', { class: 'row__title' }, 'Start with a tool-permission check'),
        h('span', { class: 'row__sub' }, 'Open the MCP tool authority component to read what it does, and what is proved about it.'))))) : null,
      h('h2', { class: 'section-title' }, 'Families'),
      famRows,
      h('h2', { class: 'section-title' }, `The ${t.kernels + t.cores} proved computations`),
      h('p', { class: 'small muted' }, `Four are at the centre and belong to the toolkit itself; the other ${t.kernels} are inside components, each joined to its component by a stem.`),
      computations);
  }

  // The picture read from the centre out, one line per layer, each with
  // the mark the map draws for it.
  function layersGuide() {
    const t = model.totals;
    const sample = model.kernels.find((k) => k.verifiedTasks) || model.kernels[0];
    const rows = [
      [dialGlyph(sample?.verifiedTasks || 6, sample?.mutants.length || 2, 26, { numeral: false }), 'Proof dials', `Proved computations, ${t.cores} at the centre and ${t.kernels} on stems from the component that runs them. Each tick round a dial is one proof check that passed; each small cross is a broken copy the prover rejected.`],
      [backingGlyph('computes', 'mark'), 'Components', `The ${t.components} mechanisms on the ring, in ${count(new Set(model.components.map((c) => c.family)).size, 'family', 'families')}. The shape of each mark stands for how the component is backed.`],
      [h('span', { class: 'guide__rings' }, TRACKS.map((tr) => ringSwatch(tr, tr.ink === 'unknown' ? 'unknown' : 'has'))), 'Eight rings', 'Kinds of recorded evidence, one cell per component. An empty cell means nothing of that kind is recorded for the component.'],
    ];
    if (t.rules) {
      rows.push([keyGlyph('cites'), 'Citations', `A tick per component, longer the more rules its own record cites: ${t.citations} citations in all.`],
        [h('span', { class: 'guide__rules' }, ruleGlyph('principle'), ruleGlyph('axiom'), ruleGlyph('anti_principle')), 'Rules', `The written rules on the outer circles: ${t.principles} principles, the ${t.axioms} axioms they rest on, and ${t.failures} failure modes.`]);
    }
    return h('div', { class: 'guide' },
      h('h2', { class: 'section-title guide__title' }, 'From the centre of the map outward'),
      h('ol', { class: 'guide__rows' }, rows.map(([mark, name, words]) => h('li', { class: 'guide__row' },
        h('span', { class: 'guide__mark' }, mark), h('span', { class: 'guide__name' }, name), h('span', { class: 'guide__words' }, words)))),
      t.rules ? h('button', { type: 'button', class: 'textbtn', onclick: () => showView('doctrine') }, 'List the rules') : null);
  }

  function filtersView() {
    const wrap = h('div', {}, h('h2', { class: 'section-title' }, 'Filters'),
      h('p', { class: 'small muted' }, 'Pick one value per filter. Filters combine with each other and with the search. Each number counts all the components, not only those shown.'));
    const data = model?.filters;
    if (!data) { wrap.append(h('p', { class: 'muted' }, 'Loading the filter values…')); return wrap; }
    for (const f of FACETS) {
      const values = data[f] || [];
      if (!values.length) continue;
      const group = h('div', { class: 'facet', role: 'group', 'aria-label': FACET_TITLES[f] }, h('h3', {}, FACET_TITLES[f]));
      const choices = h('div', { class: 'facet__choices' });
      for (const v of values) {
        choices.append(h('button', {
          type: 'button', class: 'chip', 'aria-pressed': state[f] === v.value ? 'true' : 'false', title: v.description || '',
          onclick: () => { state[f] = state[f] === v.value ? '' : v.value; commitQuery(); showView('filters'); },
        }, f === 'evidence_class' ? backingGlyph({ external_subprocess_witness: 'tool', bounded_runtime_computation: 'bounded', verified_macro_body_import: 'import', semantic_validator: 'contract', algorithmic_projection: 'computes' }[v.value]) : null,
        classWords(f, v.value), h('span', { class: 'chip__n' }, String(v.component_count))));
      }
      group.append(choices);
      wrap.append(group);
    }
    wrap.append(h('div', { class: 'actions' }, h('button', { type: 'button', class: 'btn', onclick: () => showView('index') }, 'List the matching components')));
    return wrap;
  }

  /* ---- The doctrine --------------------------------------------------------- */
  // The halo read as a list: each rule with a strip of the components that
  // cite it, in the ring's order, so a rule reads against the map as a ring
  // does. Witnesses its routing names are outlined in the strip.
  function citeStrip(rule, order) {
    const cited = new Set(rule.citedBy), witness = new Set(rule.witnesses);
    const cell = 4, gap = 1, famGap = 4;
    let x = 0;
    const rects = [];
    order.forEach((group, gi) => {
      if (gi) x += famGap;
      for (const c of group) {
        rects.push(svg('rect', { x, y: 0, width: cell, height: 12, rx: 0.6, class: `cell cell--${cited.has(c.id) ? 'has' : 'empty'}${witness.has(c.id) ? ' cell--witness' : ''}` }));
        x += cell + gap;
      }
    });
    return svg('svg', { class: 'strip strip--doctrine', viewBox: `0 0 ${x - gap} 12`, preserveAspectRatio: 'none', 'aria-hidden': 'true', focusable: 'false' }, rects);
  }
  const ruleKey = (r) => `rule:${r.id}`;
  function ruleTies(r) {
    if (r.kind === 'principle') return r.restsOn.length ? `Rests on ${r.restsOn.join(', ')}` : 'Rests on no recorded axiom';
    if (r.kind === 'anti_principle') return r.threatens.length ? `Threatens ${r.threatens.join(', ')}` : 'Tied to no recorded axiom';
    const ties = `${count(r.principles.length, 'principle')} rest on it, ${count(r.failures.length, 'failure mode')} threaten it`;
    return r.support ? `${ties} · support: ${supportWords(r.support.verdict)[2].toLowerCase()}` : ties;
  }
  function ruleRow(r, order) {
    const cited = r.citedBy.length;
    return h('li', { class: 'ring-row rule-row' }, h('button', {
      type: 'button', class: 'ring-row__go',
      onclick: () => map?.select(ruleKey(r)),
      onpointerenter: () => map?.hoverKey(ruleKey(r)),
      onpointerleave: () => map?.hoverKey(null),
      onfocus: () => map?.hoverKey(ruleKey(r)),
      onblur: () => map?.hoverKey(null),
    },
    h('span', { class: 'ring-row__title' }, ruleGlyph(r.kind), h('span', { class: `doc-id doc-id--${r.kind}` }, r.id), r.title),
    h('span', { class: `ring-row__count figures${cited ? '' : ' is-unknown'}` }, r.kind === 'anti_principle' ? 'not cited' : `${cited} of ${model.totals.components}`),
    h('span', { class: 'ring-row__by' }, r.reader?.plain ? plainSub(r) : ruleTies(r)),
    r.reader?.plain ? h('span', { class: 'ring-row__by rule-row__ties' }, ruleTies(r)) : null,
    r.kind === 'anti_principle' ? null : citeStrip(r, order)));
  }
  function doctrineView() {
    if (!model) return h('p', { class: 'muted' }, 'Loading…');
    if (!model.rules.length) {
      return h('div', {}, h('h2', { class: 'section-title' }, 'Rules'),
        h('p', { class: 'muted' }, 'This snapshot has no written rules. Rebuild the component index from this repository to include them.'));
    }
    const t = model.totals;
    const order = ringOrder();
    const part = (kind, title, note) => [
      h('h2', { class: 'section-title' }, title), h('p', { class: 'small muted' }, note),
      h('ol', { class: 'rings' }, model.rules.filter((r) => r.kind === kind).map((r) => ruleRow(r, order)))];
    return h('div', {},
      h('div', { class: 'ledger' },
        h('div', { class: 'ledger__item' }, h('span', { class: 'ledger__n ink-doctrine-text' }, String(t.axioms)), h('span', { class: 'ledger__l' }, 'axioms (basic assumptions)')),
        h('div', { class: 'ledger__item' }, h('span', { class: 'ledger__n ink-doctrine-text' }, String(t.principles)), h('span', { class: 'ledger__l' }, 'principles resting on them')),
        h('div', { class: 'ledger__item' }, h('span', { class: 'ledger__n ink-threat-text' }, String(t.failures)), h('span', { class: 'ledger__l' }, 'failure modes that would break them')),
        h('div', { class: 'ledger__item' }, h('span', { class: 'ledger__n' }, String(t.citations)), h('span', { class: 'ledger__l' }, `citations from ${count(model.components.filter((c) => c.ruleIds?.length).length, 'component')}`))),
      h('p', { class: 'small muted' }, 'Axioms are the basic assumptions, principles the working rules that follow from them, failure modes the known ways of breaking them. A strip shows which components list a rule.'),
      ...part('axiom', `The ${t.axioms} axioms`, 'On the middle circle. The arcs around each axiom are its obligations, coloured by what the support checker found when this snapshot was built.'),
      ...part('principle', `The ${t.principles} principles`, 'On the inner circle. Each rests on one or more axioms and is joined to them by a line.'),
      ...part('anti_principle', `The ${t.failures} failure modes`, 'On the outer circle. Each names a way of breaking the axioms it is joined to by a dashed line. Components do not cite failure modes.'));
  }

  function ruleRows(ids, note) {
    const list = h('ul', { class: 'rows rows--dense' });
    for (const id of ids) {
      const r = model.ruleById.get(id);
      if (!r) continue;
      list.append(h('li', { class: 'row' }, h('button', {
        type: 'button', class: 'row__go', onclick: () => map.select(ruleKey(r)),
        onpointerenter: () => map?.hoverKey(ruleKey(r)), onpointerleave: () => map?.hoverKey(null),
      }, ruleGlyph(r.kind), h('span', { class: 'row__title' }, h('span', { class: `doc-id doc-id--${r.kind}` }, r.id), ' ', r.title),
      h('span', { class: 'row__sub' }, note ? note(r) : ruleKindWords(r.kind)))));
    }
    return list;
  }
  function componentRows(ids, sub) {
    const list = h('ul', { class: 'rows rows--dense' });
    for (const id of ids) {
      const c = model.byId.get(id);
      if (!c) continue;
      list.append(h('li', { class: 'row' }, h('button', {
        type: 'button', class: 'row__go', onclick: () => map.select(`comp:${id}`),
        onpointerenter: () => map?.hoverKey(`comp:${id}`), onpointerleave: () => map?.hoverKey(null),
      }, backingGlyph(c.backing, c.kernelId ? 'mark--proved' : 'mark'), h('span', { class: 'row__title' }, c.title),
      h('span', { class: 'row__sub' }, sub ? sub(c) : familyName(c.family)))));
    }
    return list;
  }
  // A rule's card leads with what it means, in a reader's words (the
  // doctrine's reader content), then what this snapshot records about it,
  // then what the map shows; the rule as written in its source file, and
  // its formal clause, fold away beneath.
  async function ruleCard(o) {
    const r = o.rule;
    const rd = r.reader;
    const mine = ++cardRun;
    const order = ringOrder();
    const total = model.totals.components;
    const sourcePath = (r.sourceRef || '').split('::')[0];
    const sourceLink = sourceHref(model.source, sourcePath);
    const card = h('div', { class: 'rule-card' },
      cardHead([ruleGlyph(r.kind), h('span', { class: `card-kind__rule doc-id--${r.kind}` }, `${ruleKindWords(r.kind)} · ${r.id}`)]),
      contextLine((ruleKindPlain(r.kind) || '').replace(/^./, (ch) => ch.toUpperCase())),
      h('h2', { class: 'card-title' }, r.title),
      h('p', { class: 'rule-plain' }, rd?.plain || r.plain || 'No reader wording is recorded in this snapshot.'));

    // The map fact: exactly the components whose own records cite it.
    const n = r.citedBy.length;
    const fact = h('div', { class: 'mapfact' });
    if (r.kind === 'anti_principle') {
      // No record cites a failure mode; its reach is derived through the
      // axioms it would break, and the card says so in the same breath.
      const e = r.exposed.size;
      fact.classList.add('mapfact--threat');
      fact.append(h('p', { class: 'mapfact__n figures' }, h('strong', {}, `${e} / ${total}`), ` components exposed through ${r.threatens.join(', ') || 'its axioms'} · ${total - e} are not`),
        h('p', { class: 'mapfact__limit' }, EXPOSURE_WORDS));
    } else {
      fact.append(h('p', { class: 'mapfact__n figures' }, h('strong', {}, `${n} / ${total}`), ` components cite this rule · ${total - n} do not`),
        h('p', { class: 'mapfact__limit' }, CITATION_WORDS));
    }
    card.append(fact);

    // What it is tied to, as chips that light and open the other rule.
    const chipRow = (label, ids) => (ids.length ? h('div', { class: 'tie' }, h('span', { class: 'tie__label' }, label),
      h('span', { class: 'tie__chips' }, ids.map((id) => {
        const t = model.ruleById.get(id);
        return t ? h('button', { type: 'button', class: `idchip doc-id--${t.kind}`, title: t.title,
          onclick: () => map.select(ruleKey(t)), onpointerenter: () => map?.hoverKey(ruleKey(t)), onpointerleave: () => map?.hoverKey(null),
          onfocus: () => map?.hoverKey(ruleKey(t)), onblur: () => map?.hoverKey(null) }, id) : null;
      }))) : null);
    if (r.kind === 'principle') card.append(chipRow('Rests on', r.restsOn) || h('p', { class: 'small muted' }, 'Rests on no recorded axiom.'));
    if (r.kind === 'anti_principle') card.append(chipRow('Would break', r.threatens));
    if (r.kind === 'axiom') card.append(chipRow('Resting on it', r.principles), chipRow('Would be broken by', r.failures));

    // Citers by family: n of the family's m, each expanding to its citers
    // (for a failure mode, the components exposed through its axioms).
    const exposing = r.kind === 'anti_principle';
    const memberIds = exposing ? [...r.exposed.keys()] : r.citedBy;
    if (memberIds.length) {
      const cited = new Set(memberIds);
      const fams = h('ul', { class: exposing ? 'citers citers--threat' : 'citers' });
      const groups = arrange(model.components).sectors;
      for (const sector of groups) {
        const members = sector.members.map((id) => model.byId.get(id)).filter(Boolean);
        if (!members.length) continue;
        const citers = members.filter((c) => cited.has(c.id));
        const list = h('ul', { class: 'rows rows--dense citers__list', hidden: true });
        for (const c of citers) {
          list.append(h('li', { class: 'row' }, h('button', {
            type: 'button', class: 'row__go', onclick: () => map.select(`comp:${c.id}`),
            onpointerenter: () => map?.hoverKey(`comp:${c.id}`), onpointerleave: () => map?.hoverKey(null),
            onfocus: () => map?.hoverKey(`comp:${c.id}`), onblur: () => map?.hoverKey(null),
          }, backingGlyph(c.backing, c.kernelId ? 'mark--proved' : 'mark'), h('span', { class: 'row__title' }, c.title),
            exposing ? h('span', { class: 'row__via figures' }, `via ${r.exposed.get(c.id).join(', ')}`) : null)));
        }
        const toggle = h('button', { type: 'button', class: 'citers__go', 'aria-expanded': 'false', disabled: citers.length ? null : true },
          h('span', { class: 'citers__name' }, familyName(members[0].family)),
          h('span', { class: 'citers__n figures' }, `${citers.length}/${members.length}`),
          h('span', { class: 'citers__bar', 'aria-hidden': 'true' }, members.map((c) => h('i', { class: cited.has(c.id) ? 'on' : '' }))));
        toggle.addEventListener('click', () => {
          const open = toggle.getAttribute('aria-expanded') !== 'true';
          toggle.setAttribute('aria-expanded', String(open));
          list.hidden = !open;
        });
        fams.append(h('li', { class: 'citers__fam' }, toggle, list));
      }
      card.append(h('h3', { class: 'section-title' }, exposing ? 'Exposed components, by family' : 'Components that cite it, by family'),
        h('p', { class: 'small muted' }, exposing
          ? 'Open a family to list the components exposed through this failure mode’s axioms. Point at one to draw the citation that exposes it on the map; click it to open it.'
          : 'Open a family to list the components that cite this rule. Point at one to draw its line on the map; click it to open it.'), fams);
    }

    // Then the reader's explanation.
    if (rd?.analogy) {
      card.append(h('div', { class: 'rule-analogy' }, h('span', { class: 'rule-analogy__label' }, 'Think of it like this'), h('p', {}, rd.analogy)));
    }
    if (rd?.whyItMatters) card.append(h('h3', { class: 'section-title' }, 'Why it matters'), h('p', { class: 'rule-why' }, rd.whyItMatters));
    if (rd?.example) {
      const ex = h('div', { class: 'rule-example' }, h('h3', { class: 'section-title' }, 'An example from these components'), h('p', {}, rd.example));
      if (rd.exampleIds.length) ex.append(componentRows(rd.exampleIds));
      card.append(ex);
    }
    if (rd?.counterexample) card.append(h('h3', { class: 'section-title' }, 'What breaking it looks like'), h('p', { class: 'rule-counter' }, rd.counterexample));
    if (rd?.misread) card.append(h('h3', { class: 'section-title' }, 'Easy to misread'), h('p', { class: 'small' }, rd.misread));
    if (!rd) card.append(h('p', { class: 'note' }, 'This index carries no reader wording for the rules, so their own text is shown. Rebuild it from this repository for the plain version.'));

    // What else this snapshot records about it.
    const facts = h('ol', { class: 'stations' });
    if (rd) {
      const guard = r.kind === 'anti_principle';
      const where = rd.enforcedIn.map((id) => model.byId.get(id)?.title).filter(Boolean).join('; ');
      facts.append(station(keyGlyph('caller'), guard ? 'Guarded' : 'Enforced', rd.enforcedIn.length
        ? `Its write-up names ${count(rd.enforcedIn.length, 'component')} ${guard ? 'that guard against it' : 'where it is enforced'}: ${where}.`
        : `Its write-up names nowhere it is ${guard ? 'guarded against' : 'enforced'}.`, rd.enforcedIn.length ? 'has' : 'empty'));
    }
    if (r.kind === 'axiom') {
      facts.append(station(ruleGlyph('axiom'), 'Support checker', r.support ? `${supportWords(r.support.verdict)[0]} Computed when this snapshot was built.` : 'No verdict is recorded in this snapshot.', r.support ? 'has' : 'unknown'));
      if (r.witnesses.length) facts.append(station(keyGlyph('caller'), 'Witnesses', `Its routing names ${count(r.witnesses.length, 'component')} by hand as computing part of it.`));
    }
    const factsTitle = r.kind === 'axiom' ? (rd ? 'Where it is enforced, and its support' : 'Its support') : r.kind === 'anti_principle' ? 'What guards against it' : 'Where it is enforced';
    if (facts.childElementCount) card.append(h('h3', { class: 'section-title' }, factsTitle), facts);

    if (r.kind === 'axiom' && r.obligations.length) {
      const list = h('ol', { class: 'obligations' });
      for (const ob of r.obligations) {
        const [words, ink] = obligationWords(ob.computed);
        list.append(h('li', { class: `obligation obligation--${ink}` }, h('span', { class: 'obligation__arc', 'aria-hidden': 'true' }),
          h('span', {}, h('span', { class: 'obligation__predicate' }, ob.predicate || ob.id), h('span', { class: 'obligation__status' }, `${words}${ob.required ? '' : ' · optional'}`))));
      }
      card.append(h('h3', { class: 'section-title' }, `Its checkable parts (${r.obligations.length})`),
        h('p', { class: 'note' }, 'Its formal clause split into checkable parts, each drawn as an arc around its mark, in the colour of what the support checker found when the snapshot was built. None of these states is a pass.'), list);
    }
    if (r.kind === 'axiom') {
      if (r.principles.length) card.append(h('h3', { class: 'section-title' }, `Principles resting on it (${r.principles.length})`), ruleRows(r.principles, (p) => plainSub(p)));
      if (r.failures.length) card.append(h('h3', { class: 'section-title' }, `Failure modes that would break it (${r.failures.length})`), ruleRows(r.failures, (p) => plainSub(p)));
      if (r.witnesses.length) {
        const cites = new Set(r.citedBy);
        card.append(h('h3', { class: 'section-title' }, `Components named as witnesses (${r.witnesses.length})`),
          h('p', { class: 'note' }, 'Named by hand as computing part of this axiom from lower-level evidence; not checked here. A witness is a separate relation from a citation.'),
          componentRows(r.witnesses, (c) => (cites.has(c.id) ? `${familyName(c.family)} · also cites it` : `${familyName(c.family)} · does not cite it`)));
      }
    }
    if (r.kind !== 'anti_principle' && n) {
      card.append(h('details', { class: 'fullwriteup' }, h('summary', {}, `All ${count(n, 'component')} that cite it, in map order`),
        citeStrip(r, order), h('p', { class: 'note', 'data-cite-note': '' }, 'Each is read from that component’s own record.'),
        componentRows(r.citedBy)));
    }
    card.append(mapDetails(o));
    const source = h('details', { class: 'fullwriteup rule-source' }, h('summary', {}, `As written in ${sourcePath || 'its source'}`),
      h('div', { class: 'rule-statement' }, r.statement ? statementBlock(r.statement) : h('p', {}, r.plain || 'Not recorded.')),
      r.formalClause ? h('p', { class: 'statement' }, r.formalClause) : null);
    card.append(source, h('div', { class: 'actions' },
      focusButton(o),
      sourceLink ? h('a', { class: 'btn', href: sourceLink, rel: 'noopener', target: '_blank' }, `Open ${sourcePath}`) : null,
      h('a', { class: 'btn', href: withQuery('/graph', { type: 'doctrine_ref', id: r.id }), 'data-route': '' }, 'Related records')), stepBack());
    clear(body).append(card);
    body.scrollTop = 0;
    // The rule's own record from the API, when this backend serves it.
    try {
      const envelope = await getEnvelope(apiPath('doctrine', r.id), { signal });
      if (mine !== cardRun || destroyed || envelope.revision !== model.revision) return;
      const detail = envelope.data || {};
      const basis = [...new Set((detail.citations || []).map((c) => c.basis).filter(Boolean))];
      if (basis.includes('authored_atlas_row')) card.querySelector('[data-cite-note]')?.replaceChildren('Each is read from that component’s row in core/organ_atlas.json.');
    } catch {
      // An older backend has no doctrine route; the snapshot's overview stands.
    }
  }
  // A rule as written. A failure mode's source is a row of a table, so it
  // is set as its column names beside its cells, not as raw pipes.
  function statementBlock(text) {
    const lines = text.split('\n').map((l) => l.trim()).filter(Boolean);
    if (lines.length >= 3 && lines.every((l) => l.startsWith('|')) && /^\|[\s:|-]+\|$/.test(lines[1])) {
      const cells = (l) => l.replace(/^\||\|$/g, '').split('|').map((c) => c.trim());
      const head = cells(lines[0]);
      return h('dl', { class: 'rule-table' }, lines.slice(2).map(cells).flatMap((row) => head.map((name, i) => [h('dt', {}, name), h('dd', {}, row[i] || '')])));
    }
    return renderWriteup(text, { skipTitle: true, ...model.links });
  }
  // A rule's plain line for a list row, short.
  function plainSub(p) {
    const text = p.reader?.plain || ruleKindWords(p.kind);
    return text.length > 120 ? `${text.slice(0, 119).replace(/\s+\S*$/, '')}…` : text;
  }

  /* ---- Cards for a chosen object -------------------------------------------- */
  // A card's first line names the kind of thing and, on the right, the way
  // back: to the view it was opened from, or (`back`) to another object.
  function cardHead(kind, { back = null } = {}) {
    const label = back ? back.label : (VIEW_SHORT[cameFrom] || 'Overview');
    const title = back ? `Back to ${back.label}` : `Back to ${VIEW_TITLES[cameFrom] || 'the overview'} (Escape)`;
    return h('div', { class: 'card-head' },
      h('p', { class: 'card-kind' }, ...kind),
      h('button', { type: 'button', class: 'card-head__back', 'aria-label': title, onclick: () => { if (back) map.select(back.key); else map.select(null); } },
        h('span', { 'aria-hidden': 'true' }, '← '), label));
  }
  // What it belongs to, in one line over its title.
  function contextLine(text, onclick) {
    return h('p', { class: 'card-context' }, onclick ? h('button', { type: 'button', class: 'card-context__go', onclick }, text) : text);
  }
  // Frames the object's neighbourhood on the map (the engine's focus, or a
  // plain choice on an engine without it).
  function focusButton(o, label = 'Focus on the map') {
    return h('button', { type: 'button', class: 'btn', 'data-focus': '', onclick: () => (map.focus ? map.focus(o.key) : map.select(o.key)) }, label);
  }
  function stepBack() {
    // A chosen object is addressable as #o=<key>, so its card can be shared.
    return h('div', { class: 'card-foot' },
      copyButton(window.location.href, 'Copy a link to this'),
      h('p', { class: 'card-hint' }, 'Press ', h('kbd', {}, 'Esc'), ` or click empty ground to go back to ${VIEW_TITLES[cameFrom] || 'the overview'}.`));
  }
  // One fact as a station: its mark, its name, and one sentence.
  function station(mark, name, sentence, state = 'has') {
    return h('li', { class: `station station--${state}` }, mark, h('p', { class: 'station__text' }, h('b', {}, `${name}. `), sentence));
  }
  // What the drawing shows for an object, folded below the reading: one
  // line per lit thing, then its limit.
  function mapDetails(o) {
    const r = readout(model, o);
    if (!r) return null;
    const text = placement(model, o);
    return h('details', { class: 'fullwriteup map-details' }, h('summary', {}, 'How it is drawn on the map'),
      h('div', { class: 'readout' },
        h('ul', { class: 'readout__lines' }, r.lines.map((l) => h('li', { class: `readout__line readout--${l.ink}` }, h('span', { class: 'readout__ink', 'aria-hidden': 'true' }),
          h('span', {}, l.mark ? h('strong', { class: 'readout__mark' }, `${l.mark}: `) : null, l.text)))),
      ),
      text ? h('p', { class: 'card-placed' }, h('span', { class: 'card-placed__mark', 'aria-hidden': 'true' }), text) : null);
  }
  function fact(facet, status, glyph) {
    const [text, caution, known] = stateWords(facet, status);
    return h('li', { class: `fact${known ? '' : ' fact--unknown'}` }, glyph || keyGlyph('record'),
      h('span', {}, h('span', { class: 'fact__text' }, text), caution ? h('span', { class: 'fact__caution' }, caution) : null));
  }
  // A limit block: what this does not establish.
  function limitBlock(label, text, attrs = {}) {
    return h('div', { class: 'limit', ...attrs }, h('span', { class: 'limit__label' }, label), text);
  }
  // "N proof checks passed · M broken copies rejected", with the dial.
  function proofCounts(p, size = 44) {
    return h('div', { class: 'proofcount' }, dialGlyph(p.verifiedTasks || 0, p.mutants.length, size),
      h('p', { class: 'proofcount__text figures' }, h('strong', {}, count(p.verifiedTasks || 0, 'proof check')), ' passed · ',
        h('strong', {}, count(p.mutants.length, 'broken copy', 'broken copies')), ' rejected',
        h('span', { class: 'proofcount__note' }, `Saved results${p.dafnyVersion ? ` from Dafny ${p.dafnyVersion.split('+')[0]}` : ''}.`)));
  }

  // One component's column of the rings, as eight evidence rows in the
  // key's order: ordinal, swatch, name and a state word, never a fraction.
  function columnFacts(c, facets) {
    const k = c.kernelId ? model.kernelById.get(c.kernelId) : null;
    const kept = c.receipts.filter((r) => r.availability === 'available');
    const dated = kept.filter((r) => r.createdAt).map((r) => r.createdAt).sort();
    const detail = {
      proof: k ? `${proofShortName(k)}, proved in Dafny.` : '',
      variants: k ? `${count(k.mutants.length, 'broken copy', 'broken copies')} rejected by the prover.` : '',
      bound: k ? 'Fingerprints matched when this snapshot was made.' : '',
      caller: k ? 'A link written in its code, not a record of a run.' : '',
      lean: 'About the example mathematics, not this component’s code.',
      replay: 'Set up is not the same as passed.',
      saved: kept.length ? (dated.length ? `Latest ${dayWords(dated[dated.length - 1])}. Not rerun against today’s code.` : 'Dates not saved. Not rerun against today’s code.') : '',
      whole: 'Nobody has matched its whole claim to checks.',
    };
    const list = h('ol', { class: 'evidence' });
    TRACKS.forEach((t, i) => {
      const st = ringState(t, c);
      list.append(h('li', { class: `evidence__row evidence__row--${st.state}`, title: t.line },
        h('span', { class: 'evidence__no figures' }, ordinal(i)), swatch(t, st.state),
        h('span', { class: 'evidence__name' }, t.short),
        h('span', { class: 'evidence__state figures' }, st.word),
        st.state !== 'empty' && detail[t.id] ? h('span', { class: 'evidence__detail' }, detail[t.id]) : null));
    });
    if (facets?.host_tests?.status === 'linked_not_run') {
      list.append(h('li', { class: 'evidence__row evidence__row--extra' }, h('span', { class: 'evidence__no' }), h('span', { class: 'swatch', style: '--ink-fill: var(--ring-caller)', 'aria-hidden': 'true' }),
        h('span', { class: 'evidence__name' }, 'Tests listed'), h('span', { class: 'evidence__state' }, 'Not run for this page')));
    }
    return list;
  }
  async function componentCard(o) {
    const c = o.comp;
    const mine = ++cardRun;
    const column = h('div', {}, columnFacts(c, null));
    const fullWriteup = h('details', { class: 'fullwriteup' }, h('summary', {}, 'Full write-up'),
      h('div', { 'data-writeup': '' }, h('p', { class: 'muted small' }, 'Loading the write-up…')));
    let guide, guideReady = false, guideRendered = false;
    const showGuide = () => {
      if (!fullWriteup.open || !guideReady || guideRendered || mine !== cardRun || destroyed) return;
      fullWriteup.querySelector('[data-writeup]').replaceChildren(renderGuide(guide, model.links, { skipPlain: !!c.plain }));
      guideRendered = true;
    };
    fullWriteup.addEventListener('toggle', showGuide);
    const card = h('div', { class: 'component-card' },
      cardHead([backingGlyph(c.backing, c.kernelId ? 'mark--proved' : 'mark'), 'Component', h('span', { class: 'card-kind__sub' }, `· ${classWords('evidence_class', c.evidenceClass)}`)]),
      contextLine(familyName(c.family)),
      h('h2', { class: 'card-title' }, c.title),
      h('p', { class: 'card-plain component-summary' }, c.summary || c.plain || 'No description is recorded.'),
      limitBlock('What it covers', 'Loading…', { 'data-limit': '' }),
      h('div', { class: 'section-head' }, h('h3', { class: 'section-title' }, 'Checks recorded for it'), h('span', { class: 'section-aside' }, 'Numbered from the component outward')),
      column,
      h('p', { class: 'note' }, '“Not recorded” means absent from this snapshot, not a failed check.'));
    if (c.kernelId) {
      const k = model.kernelById.get(c.kernelId);
      card.append(h('section', { class: 'component-proof', 'aria-label': 'Proved part' },
        h('h3', { class: 'section-title' }, `Proved part: ${proofShortName(k)}`),
        proofCounts(k, 40),
        h('p', { class: 'small' }, 'The proof covers this one computation under its written assumptions.'),
        h('div', { class: 'actions' },
          h('button', { type: 'button', class: 'btn btn--ink', onclick: () => map.select(`kernel:${k.id}`) }, 'Read the proof'),
          h('a', { class: 'btn', href: `/proofs/${encodeURIComponent(k.id)}`, 'data-route': '' }, 'Open the proof page'))));
    }
    if (c.plain) card.append(h('details', { class: 'fullwriteup plain-explanation' }, h('summary', {}, 'Explanation in plain words'), h('p', { class: 'small', 'data-plain': '' }, c.plain)));
    const cites = c.ruleIds || [];
    const witnessFor = model.rules.filter((r) => r.witnesses.includes(c.id)).map((r) => r.id);
    if (cites.length || witnessFor.length) {
      card.append(h('h3', { class: 'section-title' }, `Rules its record cites (${cites.length})`),
        h('p', { class: 'note' }, `${CITATION_WORDS} Point at one to draw its line on the map.`),
        ruleRows(cites, (r) => plainSub(r)));
      if (witnessFor.length) {
        card.append(h('p', { class: 'note' }, `The routing registry also names it as a witness for ${witnessFor.join(', ')}: a component said, by hand, to compute part of that axiom from lower-level evidence.`));
      }
    } else if (model.rules.length) {
      card.append(h('p', { class: 'note' }, 'Its record cites no rule.'));
    }
    const doctrine = model.rules.length ? [] : c.doctrineIds.map((id) => model.doctrine.get(id)).filter(Boolean);
    if (doctrine.length) {
      card.append(h('h3', { class: 'section-title' }, 'Principles it cites'),
        h('ul', { class: 'doctrine' }, doctrine.map((d) => h('li', {}, h('span', { class: `doc-id doc-id--${d.kind}` }, d.id), ' ', h('strong', {}, d.title),
          h('span', { class: 'muted small' }, ` ${d.kind === 'anti_principle' ? 'Failure mode' : d.kind === 'axiom' ? 'Axiom' : 'Principle'}`)))));
    }
    const wired = model.wires.filter(([a, b]) => a === c.id || b === c.id).map(([a, b]) => (a === c.id ? b : a));
    const imports = [...c.importsOut.map((e) => [e.to, e]), ...c.importsIn.map((e) => [e.from, e])];
    if (wired.length || imports.length) {
      const list = h('ul', { class: 'rows' });
      const row = (other, sub) => h('li', { class: 'row' }, h('button', { type: 'button', class: 'row__go', onclick: () => map.select(`comp:${other.id}`),
        onpointerenter: () => map?.hoverKey(`comp:${other.id}`), onpointerleave: () => map?.hoverKey(null) },
        backingGlyph(other.backing, other.kernelId ? 'mark--proved' : 'mark'), h('span', { class: 'row__title' }, other.title), h('span', { class: 'row__sub' }, sub)));
      for (const [id, e] of imports) {
        const other = model.byId.get(id);
        if (other) list.append(row(other, e.from === c.id ? 'Its code imports this one' : 'This one’s code imports it'));
      }
      for (const id of wired) {
        const other = model.byId.get(id);
        if (other) list.append(row(other, `Declared connection · ${familyName(other.family)}`));
      }
      card.append(h('h3', { class: 'section-title' }, `Connections (${wired.length + imports.length})`),
        h('p', { class: 'note' }, 'Declared in the source code. They say these components are meant to work together, not that one has called the other.'), list);
    }
    card.append(h('h3', { class: 'section-title' }, `Past runs (${c.receipts.length})`),
      runsStrip(c.receipts, model.source),
      h('p', { class: 'note' }, 'Newest first. Saved results of earlier runs.'),
      fullWriteup, mapDetails(o));
    card.append(h('div', { class: 'actions' },
      focusButton(o),
      h('a', { class: 'btn btn--ink', href: `/components/${encodeURIComponent(c.id)}`, 'data-route': '' }, 'Open the component page'),
      h('a', { class: 'btn', href: withQuery('/graph', { type: 'organ', id: c.id }), 'data-route': '' }, 'Related records')), stepBack());
    clear(body).append(card);
    body.scrollTop = 0;
    let detail;
    try {
      const envelope = await getEnvelope(apiPath('components', c.id), { signal });
      if (envelope.revision !== model.revision) throw new ApiError('revision', 'The index changed. Reload the map to read this component.');
      detail = envelope.data;
    } catch (error) {
      if (mine !== cardRun || destroyed) return;
      card.querySelector('[data-limit]').replaceChildren(h('span', { class: 'limit__label' }, 'What it covers'), `This component’s details could not be loaded: ${error.message}`);
      card.querySelector('[data-writeup]').replaceChildren(h('p', { class: 'note' }, 'The write-up could not be loaded with this component.'));
      return;
    }
    if (mine !== cardRun || destroyed) return;
    guide = detail.guide;
    guideReady = true;
    showGuide();
    const claim = detail.claim || {};
    const facets = claim.card?.assurance_facets || {};
    card.querySelector('[data-limit]').replaceChildren(h('span', { class: 'limit__label' }, 'What it covers'), claim.claim_ceiling_restated || claim.claim_ceiling || 'No limit is written down.');
    column.replaceChildren(columnFacts(c, facets));
  }

  function proofFacts(p) {
    return h('ul', { class: 'facts' },
      h('li', { class: 'fact' }, keyGlyph('task'), h('span', {}, `Dafny ${p.dafnyVersion.split('+')[0] || ''} passed ${count(p.verifiedTasks || 0, 'proof check')}.`)),
      h('li', { class: 'fact' }, keyGlyph('variant'), h('span', {}, `${count(p.mutants.length, 'deliberately broken copy', 'deliberately broken copies')} failed the proof, as they should.`)),
      fact('proof_binding', p.binding, keyGlyph('generated')),
      fact('fresh_prover', p.freshProver, keyGlyph('absent')),
      fact('requirements_review', p.requirementsReview, keyGlyph('absent')));
  }

  // The chain from the written rules to the component that runs them.
  function chainStations(k, comp) {
    const gen = k.generatedRefs.length;
    const [bindText] = stateWords('proof_binding', k.binding);
    return h('ol', { class: 'stations chain' },
      station(keyGlyph('kernel'), 'Written rules', `The Dafny specification the prover checked the computation against${k.specificationRefs.length ? `, in ${count(k.specificationRefs.length, 'file')}` : ''}.`),
      station(keyGlyph('generated'), 'Generated Python', `${gen ? `${count(gen, 'file')} that Dafny produced from the proved code. ` : 'The code Dafny produced from the proved code. '}${bindText}`, gen ? 'has' : 'empty'),
      station(keyGlyph('caller'), 'Caller', comp ? 'The component’s own code calls the generated computation directly; a link in the code, not a record of a run.' : 'No caller is recorded.', comp ? 'has' : 'empty'),
      comp ? h('li', { class: 'station station--has' }, backingGlyph(comp.backing, 'mark--proved'),
        h('p', { class: 'station__text' }, h('b', {}, 'Component. '), h('button', { type: 'button', class: 'card-context__go', onclick: () => map.select(`comp:${comp.id}`) }, comp.title), '. The rest of it is outside this proof.'))
        : station(keyGlyph('absent'), 'Component', 'It is used by no component.', 'empty'));
  }

  function kernelCard(o) {
    const k = o.kernel;
    const comp = o.componentId ? model.byId.get(o.componentId) : null;
    const isOwnership = model.ownership && model.ownership.proof_id === k.id;
    clear(body).append(h('div', { class: 'kernel-card' },
      cardHead([keyGlyph('kernel'), 'Proved computation'], comp ? { back: { key: `comp:${comp.id}`, label: 'Its component' } } : {}),
      comp ? contextLine(`Inside ${comp.title}`, () => map.select(`comp:${comp.id}`)) : null,
      h('h2', { class: 'card-title' }, proofShortName(k)),
      h('div', { class: 'promise' }, h('span', { class: 'promise__label' }, 'The statement proved'), h('p', { class: 'promise__text' }, k.statement || 'No statement is recorded.')),
      proofCounts(k),
      limitBlock('What the proof leaves out', k.limits || 'No limit is written down.'),
      h('h3', { class: 'section-title' }, 'From written rules to the component'),
      chainStations(k, comp),
      h('div', { class: 'actions' },
        focusButton(o),
        h('a', { class: 'btn btn--ink', href: `/proofs/${encodeURIComponent(k.id)}`, 'data-route': '' }, 'Open the proof page')),
      isOwnership ? h('div', {}, h('h3', { class: 'section-title' }, 'Why the rule had to change'), ownershipFigure(model.ownership, model.source)) : null,
      h('details', { class: 'fullwriteup tech' }, h('summary', {}, 'Technical detail'),
        h('h4', {}, 'The written rules, in Dafny'), specificationParts(k, model.source),
        h('h4', {}, 'Broken copies the prover rejected'), variantsPart(k, model.source),
        h('h4', {}, 'What is checked, and what is not'), proofFacts(k),
        h('h4', {}, 'What it takes in'), h('p', { class: 'small' }, k.inputModel || 'Not recorded.'),
        h('h4', {}, 'Assumptions'), h('p', { class: 'small' }, k.assumptions || 'Not recorded.')),
      mapDetails(o),
      stepBack()));
    body.scrollTop = 0;
  }

  function coreCard(o) {
    const c = o.core;
    const centre = c.id === 'replay_admission';
    const total = model.totals.components;
    const wrap = h('div', { class: 'kernel-card' },
      cardHead([keyGlyph('kernel'), centre ? 'The replay checker' : 'Proved computation in the toolkit']),
      contextLine(centre ? 'At the centre of the map' : 'Part of the toolkit itself, not of any one component'),
      h('h2', { class: 'card-title' }, CORE_NAMES[c.id]?.[0] || moduleWords(c.id)),
      h('p', { class: 'card-plain' }, `It ${CORE_NAMES[c.id]?.[1] || 'is part of the toolkit'}, and the toolkit calls it directly.`),
      proofCounts(c));
    if (centre) {
      const n = c.admitted.length;
      wrap.append(h('div', { class: 'mapfact' },
        h('p', { class: 'mapfact__n figures' }, h('strong', {}, `${n} / ${total}`), ` components have a rerun set up; none is run on this page`),
        h('p', { class: 'mapfact__limit' }, 'Configured is not the same as passed. It accepts a rerun only if every component is covered and each result matches what was saved.')));
    }
    wrap.append(limitBlock('What the proof leaves out', c.limits || 'No limit is written down.'),
      h('div', { class: 'promise' }, h('span', { class: 'promise__label' }, 'The statement proved'), h('p', { class: 'promise__text' }, c.statement || 'No statement is recorded.')),
      h('div', { class: 'actions' },
        focusButton(o),
        h('a', { class: 'btn btn--ink', href: `/proofs/${encodeURIComponent(c.proofId || c.id)}`, 'data-route': '' }, 'Open the proof page')));
    if (centre && c.admitted.length) {
      const list = h('ul', { class: 'rows rows--dense' });
      for (const a of c.admitted) {
        const comp = model.byId.get(a.componentId);
        list.append(h('li', { class: 'row' }, h('button', { type: 'button', class: 'row__go', onclick: () => map.select(`comp:${a.componentId}`),
          onpointerenter: () => map?.hoverKey(`comp:${a.componentId}`), onpointerleave: () => map?.hoverKey(null) },
          comp ? backingGlyph(comp.backing, comp.kernelId ? 'mark--proved' : 'mark') : keyGlyph('absent'),
          h('span', { class: 'row__title' }, comp ? comp.title : a.componentId), h('code', { class: 'row__sub row__code' }, a.route))));
      }
      wrap.append(h('h3', { class: 'section-title' }, `The ${c.admitted.length} reruns it would judge`), list);
    }
    wrap.append(h('details', { class: 'fullwriteup tech' }, h('summary', {}, 'Technical detail'),
      h('h4', {}, 'What is checked, and what is not'), proofFacts(c),
      h('h4', {}, 'Assumptions'), h('p', { class: 'small' }, c.assumptions || 'Not recorded.'),
      h('h4', {}, 'Who calls it'),
      h('ul', { class: 'callers' }, c.callers.map((ref) => {
        const { api, fn } = callerWords(ref);
        const href = sourceHref(model.source, ref);
        const inner = [h('strong', {}, api), fn ? h('span', { class: 'muted' }, ` · ${fn.replace(/_/g, ' ')}`) : null];
        return h('li', {}, href ? h('a', { href, rel: 'noopener', target: '_blank' }, inner) : inner);
      })),
      h('h4', {}, 'Broken copies the prover rejected'), variantsPart(c, model.source),
      h('div', { 'data-writeup': '' })),
      mapDetails(o), stepBack());
    clear(body).append(wrap);
    body.scrollTop = 0;
    const run = ++cardRun;
    loadWriteup('core', c.id, model.links, { signal }).then((el) => {
      if (run === cardRun && !destroyed) wrap.querySelector('[data-writeup]').replaceChildren(h('h4', {}, 'Its write-up'), el);
    });
  }

  function onSelect(o) {
    cardRun += 1;
    hideDock();
    const hash = o ? `#o=${encodeURIComponent(o.key)}` : '';
    history.replaceState(null, '', `${window.location.pathname}${window.location.search}${hash}`);
    if (!o) {
      explorer.dispatchEvent(new CustomEvent('explorer:released', { bubbles: true }));
      showView(panelView === 'card' ? cameFrom : panelView);
      return;
    }
    if (panelView !== 'card') cameFrom = panelView;
    panelView = 'card';
    if (!srTitle.isConnected) panel.prepend(srTitle);
    for (const b of [tabOverview, tabIndex, tabDoctrine, utilFilters, utilKey]) press(b, false);
    explorer.dispatchEvent(new CustomEvent('explorer:selected', { bubbles: true }));
    if (o.type === 'component') { componentCard(o); announce(`${o.comp.title} selected`); }
    else if (o.type === 'kernel') { kernelCard(o); announce(`${proofShortName(o.kernel)}, a proved computation, selected`); }
    else if (o.type === 'core') { coreCard(o); announce(`${CORE_NAMES[o.core.id]?.[0] || moduleWords(o.core.id)} selected`); }
    else if (o.type === 'rule') { ruleCard(o); announce(`${ruleKindWords(o.rule.kind)} ${o.rule.id}, ${o.rule.title}, selected`); }
  }

  signal?.addEventListener('abort', dispose, { once: true });
  if (signal?.aborted) { dispose(); return dispose; }

  /* ---- Boot ----------------------------------------------------------------- */
  showView(state.q ? 'index' : 'overview');
  syncFiltered();
  try {
    model = await getModel({ signal });
    setLabels(model.filters);
    syncFiltered();
  } catch (error) {
    if (destroyed) return () => {};
    status.replaceChildren(errorBlock(error, () => navigate(window.location.href, { replace: true })));
    foot.textContent = '';
    return dispose;
  }
  if (destroyed) return () => {};
  status.hidden = true;
  const src = model.source ? `, built from commit ${model.source.commit.slice(0, 10)}` : '';
  foot.textContent = `Snapshot ${model.revision.slice(0, 12)}${src}.`;
  foot.title = model.revision;
  const t = model.totals;
  if (revealPlayed) document.documentElement.classList.add('map-seen');
  // The preview dock. A hover settles after a short delay; when the pointer
  // leaves, the last preview stays a moment so it can be read.
  function showPeek(o, info) {
    clearTimeout(peekTimer);
    const kinds = ['component', 'kernel', 'core', 'rule'];
    if (o && o.key !== dismissedKey) dismissedKey = null;
    const key = o && kinds.includes(o.type) && o.key !== map?.selectedKey() && o.key !== dismissedKey ? o.key : null;
    if (key === peekKey) return;
    peekTimer = setTimeout(() => {
      if (destroyed) return;
      if (!key) { hideDock(); return; }
      peekKey = key;
      dock.replaceChildren(dockCard(o, info));
      dock.classList.add('is-on');
    }, key ? 60 : 300);
  }
  function hideDock() {
    clearTimeout(peekTimer);
    peekKey = null;
    dock.classList.remove('is-on');
  }
  function dockShown() { return dock.classList.contains('is-on'); }
  function dismissPreview() {
    dismissedKey = peekKey;
    hideDock();
    map?.hoverKey(null);
  }
  function dockCard(o, info) {
    const chosenKey = map?.selectedKey();
    const chosen = chosenKey ? map.objectFor(chosenKey) : null;
    const p = preview(model, o, chosen, info);
    const mark = o.type === 'component' ? backingGlyph(o.comp.backing, o.comp.kernelId ? 'mark--proved' : 'mark')
      : o.type === 'rule' ? ruleGlyph(o.rule.kind) : keyGlyph('kernel');
    return h('div', { class: 'dock__inner' },
      h('p', { class: 'dock__kind' }, mark, h('span', {}, 'Preview · ', p.kind)),
      h('p', { class: 'dock__name' }, p.name),
      p.relation ? h('p', { class: 'dock__relation' }, p.relation) : null,
      p.purpose ? h('p', { class: 'dock__purpose' }, p.purpose) : null,
      o.type === 'component' ? h('p', { class: 'dock__rings', 'aria-label': 'Its eight rings' }, TRACKS.map((t) => {
        const st = ringState(t, o.comp);
        return h('span', { class: 'dock__ring', title: `${t.short}: ${st.word}` }, swatch(t, st.state));
      })) : null,
      h('ul', { class: 'dock__counts figures' }, p.counts.map((c) => h('li', {}, c))),
      h('p', { class: 'dock__hint' }, 'Click to choose · ', h('kbd', {}, 'Esc'), ' to dismiss'));
  }
  // The stage's ring key opens in full when its corner has room beside the
  // drawing, and folds to a "Key" chip otherwise.
  function fitRingKey() {
    if (destroyed || !stage.clientWidth) return;
    const was = ringKey.classList.contains('is-compact');
    ringKey.classList.remove('is-compact');
    const kw = ringKey.offsetWidth, kh = ringKey.offsetHeight;
    const sw = stage.clientWidth, sh = stage.clientHeight;
    const cx = sw / 2, cy = sh / 2, reach = Math.min(sw, sh) / 2 - 12;
    const dx = Math.max(cx - (18 + kw), 0), dy = Math.max(cy - (14 + kh), 0);
    const room = sw >= 600 && Math.hypot(dx, dy) - 6 >= reach * 0.95;
    ringKey.classList.toggle('is-compact', !room);
    if (room) { ringKey.classList.remove('is-open'); ringKeyChip.setAttribute('aria-expanded', 'false'); ringKeyChip.textContent = 'Ring key'; }
    if (was !== !room) map?.resize?.();
  }

  for (const t of TRACKS) {
    const n = t.ink === 'unknown' ? null : model.components.filter((c) => c.checks[t.id]).length;
    ringCounts.get(t.id).textContent = n === null ? 'unknown' : `${n}/${model.totals.components}`;
  }
  fitRingKey();
  map = createMap(canvas, model, {
    onHover: (o, info) => showPeek(o, info),
    onSelect,
    onOpen: (o) => {
      if (o.type === 'component') navigate(`/components/${encodeURIComponent(o.id)}`);
      if (o.type === 'kernel') navigate(`/proofs/${encodeURIComponent(o.id)}`);
      if (o.type === 'core') navigate(`/proofs/${encodeURIComponent(o.core.proofId || o.id)}`);
    },
    skipReveal: revealPlayed,
  });
  revealPlayed = true;
  explorer.addEventListener('explorer:fit', () => map.fit());
  explorer.addEventListener('explorer:zoom', (e) => map.zoomBy(e.detail.direction > 0 ? 1.4 : 1 / 1.4));
  explorer.addEventListener('explorer:resize', () => { map.resize(); fitRingKey(); });
  window.addEventListener('resize', fitRingKey);
  if (state.q.trim() || FACETS.some((facet) => state[facet]) || panelView === 'index') {
    catalogueLoaded = true;
    catalogue.load(state);
  }
  if (panelView === 'overview') showView('overview');
  const wanted = decodeURIComponent((window.location.hash.match(/^#o=(.+)$/) || [])[1] || '');
  if (wanted && map.objectFor(wanted)) map.select(wanted);
  return dispose;
}

export function errorBlock(error, retry) {
  const box = h('div', { class: 'state state--error', role: 'alert', style: 'max-width:46ch;text-align:left' });
  if (error.kind === 'network') {
    box.append(h('strong', {}, 'The data server is not running. '), 'From the repository, start the explorer with ', h('code', {}, 'make explorer'), ' and reload.');
  } else if (error.kind === 'schema') {
    box.append(h('strong', {}, 'The data server sent a format this explorer cannot read. '), error.message);
  } else if (error.kind === 'not_found') {
    box.append(h('strong', {}, 'This data server is older than the explorer. '), 'Start both from this repository with ', h('code', {}, 'make explorer'), '.');
  } else if (error.kind === 'revision') {
    box.append(h('strong', {}, 'The data changed twice while the map was loading. '), 'Nothing from the two versions was combined.');
  } else {
    box.append(h('strong', {}, 'The map could not be loaded. '), error.message);
  }
  box.append(' ', h('button', { type: 'button', class: 'textbtn', onclick: retry }, 'Try again'));
  return box;
}
