// The evidence map page: the reading panel on the left, the drawing in the
// rest of the window (the universe map's explorer layout). At rest the panel
// reads the map's coverage rings as strips, one per kind of check, then the
// families and the verified computations. A chosen object gets a card. A
// chosen object is addressable as #o=<key>; search and filters live in the
// query string.

import { apiPath, getEnvelope, withQuery } from '../api.js';
import { getModel } from '../data.js';
import { announce, backingGlyph, clear, h, keyGlyph, ringStyle, ringSwatch, svg } from '../dom.js';
import {
  BACKING_ORDER, CLASS_OF_BACKING, FAMILY_ORDER, TRACKS, callerWords, classDescription, classWords, count, dayWords, familyName, moduleWords,
  proofShortName, setLabels, sourceHref, stateWords, CORE_NAMES, flowerWords,
} from '../evidence.js';
import { fetchWriteup, loadPlain, loadWriteup } from '../markdown.js';
import { wireExplorer } from '../frame.js';
import { createMap } from '../map/engine.js';
import { arrange } from '../map/layout.js';
import { FACETS, FACET_TITLES, componentRow, createCatalogue, filterSentence, readQuery, writeQuery } from './catalogue-core.js';
import { ownershipFigure, runsStrip, specificationParts, variantsPart } from './proofparts.js';
import { openExplainer } from './explain.js';

let revealPlayed = false;

const INK_CLASS = { ran: 'ink-ran', stated: 'ink-stated', saved: 'ink-saved', unknown: 'ink-unknown' };

/** A small swatch in a ring's own colour: filled, empty, or hatched. */
const swatch = (track, state) => ringSwatch(track, state);

export async function mountExplorer(root, { url, navigate }) {
  const canvas = h('canvas', { tabindex: '0', role: 'img', 'aria-label': 'Map of the Plectis components and their checks. The panel lists everything the map draws.' });
  const status = h('div', { class: 'explorer__status', role: 'status' }, 'Reading the component index…');
  const legend = h('div', { class: 'explorer__legend', 'aria-label': 'Key' },
    h('span', { class: 'key' }, keyGlyph('kernel'), 'Proved computation'),
    h('span', { class: 'key' }, keyGlyph('thread'), 'Uses proved code'),
    h('span', { class: 'key' }, keyGlyph('spoke'), 'Rerun path'),
    h('span', { class: 'key' }, backingGlyph('computes', 'mark'), 'Component (shape: its kind)'),
    h('span', { class: 'key' }, h('span', { class: 'swatch is-empty', 'aria-hidden': 'true' }), 'Not checked'),
    h('span', { class: 'key' }, h('span', { class: 'swatch ink-unknown', 'aria-hidden': 'true' }), 'Unknown'));
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
  // bottom and each ring stacked outward above it, in its own ink.
  const ringKey = h('div', { class: 'explorer__rings' },
    h('p', { class: 'ringkey__title', id: 'ringkey-title' }, 'Rings, from each component outward'),
    h('ol', { class: 'ringkey', 'aria-labelledby': 'ringkey-title', reversed: true },
      [...TRACKS].reverse().map((t) => h('li', {
        class: 'ringkey__row',
        title: `${t.title}: what it means`,
        onclick: () => openExplainer(t.id),
        onpointerenter: () => { if (!pinnedTrack) map?.emphasise(t.id); },
        onpointerleave: () => { if (!pinnedTrack) map?.emphasise(null); },
      }, swatch(t, t.ink === 'unknown' ? 'unknown' : 'has'), h('span', {}, t.short), h('span', { class: 'ringkey__by' }, t.checker)))),
    h('p', { class: 'ringkey__base' }, h('span', { class: 'ringkey__mark', 'aria-hidden': 'true' }), 'The component'),
    h('button', { type: 'button', class: 'ringkey__more', onclick: () => openExplainer() }, 'What do these mean?'));
  const stage = h('div', { class: 'explorer__stage' }, canvas, ringKey, tools, legend, status);

  const state = readQuery(url);
  const search = h('input', { type: 'search', id: 'map-find', placeholder: 'Search the components…', value: state.q, maxlength: '160', autocomplete: 'off', spellcheck: 'false' });
  const tabOverview = h('button', { type: 'button', class: 'tab', 'aria-pressed': 'true' }, 'Overview');
  const tabIndex = h('button', { type: 'button', class: 'tab', 'aria-pressed': 'false' }, 'All components');
  const utilFilters = h('button', { type: 'button', class: 'util', 'aria-pressed': 'false' }, 'Filters');
  const utilKey = h('button', { type: 'button', class: 'util', 'aria-pressed': 'false' }, 'Key');
  const filteredText = h('span', {});
  const filtered = h('div', { class: 'filtered', hidden: true }, filteredText, h('button', { type: 'button', class: 'textbtn', onclick: () => resetQuery() }, 'Reset'));
  const lede = h('p', { class: 'panel-lede' }, 'Which parts of this system are proved to follow written rules, what else checks each part, and what nobody has checked.');
  const body = h('div', { class: 'explorer__body', tabindex: '-1' });
  const foot = h('div', { class: 'explorer__foot figures' }, 'Loading…');
  // What the pointer is on, read in plain words over the panel, without
  // losing the panel's own place.
  const peek = h('div', { class: 'peek', 'aria-hidden': 'true' });
  const panel = h('aside', { class: 'explorer__panel', 'aria-label': 'Reading the map' }, peek,
    h('div', { class: 'explorer__head' },
      h('h1', { class: 'explorer__title' }, 'What’s proved, and what isn’t'),
      lede,
      h('div', { class: 'find' }, h('label', { class: 'sr-only', for: 'map-find' }, 'Find a component'), search),
      h('div', { class: 'tabs' },
        h('div', { class: 'tabs__group', role: 'group', 'aria-label': 'Read the map by' }, tabOverview, tabIndex),
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
  let panelView = 'overview';
  let destroyed = false;
  let cardRun = 0;
  let currentMatches = null;
  let pinnedTrack = null;
  const indexHost = h('div', {});
  const catalogue = createCatalogue(indexHost, {
    row: (item) => componentRow(item, {
      onPick: (it) => map && map.select(`comp:${it.organ_id}`),
      onEnter: (it) => map && map.hoverKey(`comp:${it.organ_id}`),
      onLeave: () => map && map.hoverKey(null),
    }),
    onMatches: (set) => { currentMatches = set; if (map && !pinnedTrack) map.setMatches(set); },
    onReset: () => resetQuery(),
  });

  wiringBtn.addEventListener('click', () => {
    if (!map) return;
    const on = map.showWiring(wiringBtn.getAttribute('aria-pressed') !== 'true');
    wiringBtn.setAttribute('aria-pressed', String(on));
    announce(on ? `Showing all ${model.totals.wires} declared wires` : 'Wiring hidden');
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
    // An open window (the key) handles its own keys.
    if (document.querySelector('dialog[open]')) return;
    const typing = e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement;
    if (e.key === '/' && !typing) {
      e.preventDefault(); search.focus();
    }
    // Escape lets go of whatever is chosen, wherever the focus is: first the
    // chosen object, then a ring kept lit.
    if (e.key === 'Escape' && !(typing && e.target.value) && !e.defaultPrevented) {
      if (map?.selectedKey()) { e.preventDefault(); map.select(null); }
      else if (pinnedTrack) {
        e.preventDefault();
        const row = body.querySelector('.ring-row.is-pinned');
        const track = TRACKS.find((x) => x.id === pinnedTrack);
        if (row && track) pinTrack(track, row); else { pinnedTrack = null; map?.emphasise(null); map?.setMatches(currentMatches); }
      }
    }
  }

  /* ---- Panel views -------------------------------------------------------- */
  function press(btn, on) { btn.setAttribute('aria-pressed', on ? 'true' : 'false'); }
  function showView(which) {
    panelView = which;
    press(tabOverview, which === 'overview');
    press(tabIndex, which === 'index');
    press(utilFilters, which === 'filters');
    press(utilKey, which === 'key');
    clear(body);
    if (which === 'overview') body.append(overviewView());
    if (which === 'index') body.append(h('h2', { class: 'section-title' }, `All ${model ? model.totals.components : ''} components`), indexHost);
    if (which === 'filters') body.append(filtersView());
    body.scrollTop = 0;
  }
  tabOverview.addEventListener('click', () => { map?.select(null, { camera: false }); showView('overview'); });
  tabIndex.addEventListener('click', () => { map?.select(null, { camera: false }); showView('index'); });
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
    const rows = h('ol', { class: 'rings' });
    for (const track of TRACKS) {
      const measure = track.measure ? cov[track.measure] : null;
      const n = track.ink === 'unknown' ? null : model.components.filter((c) => c.checks[track.id]).length;
      const tally = n === null ? 'unknown' : `${n} of ${t.components}`;
      let extra = '';
      if (track.id === 'saved') extra = `${count(t.receipts, 'saved result')}, ${t.unavailable} missing`;
      if (track.id === 'variants') extra = `${count(t.mutants, 'broken version')} across all 16 proved computations`;
      const row = h('li', { class: `ring-row${pinnedTrack === track.id ? ' is-pinned' : ''}` });
      row.append(h('button', {
        type: 'button', class: 'ring-row__go', 'aria-pressed': String(pinnedTrack === track.id),
        title: measure?.kind ? `The coverage view: ${measure.kind}` : '',
        onclick: () => pinTrack(track, row),
        onpointerenter: () => { if (!pinnedTrack) map?.emphasise(track.id); },
        onpointerleave: () => { if (!pinnedTrack) map?.emphasise(null); },
        onfocus: () => { if (!pinnedTrack) map?.emphasise(track.id); },
        onblur: () => { if (!pinnedTrack) map?.emphasise(null); },
      },
      h('span', { class: 'ring-row__title' }, swatch(track, track.ink === 'unknown' ? 'unknown' : 'has'), track.title),
      h('span', { class: `ring-row__count figures${n === null ? ' is-unknown' : ''}` }, tally),
      h('span', { class: 'ring-row__by' }, `${track.checker}${track.when ? ` · ${track.when}` : ''}${extra ? ` · ${extra}` : ''}`),
      strip(track, order)));
      rows.append(row);
    }
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
      h('span', { class: 'family-row__count' }, String(members.length)),
      h('span', { class: 'family-row__tally' }, formal ? `${formal} with a proved computation` : 'None with a proved computation'),
      h('span', { class: 'family-row__marks', 'aria-hidden': 'true' }, members.map((c) => backingGlyph(c.backing, c.kernelId ? 'mark--proved' : 'mark'))))));
    }
    const computations = h('ul', { class: 'rows' });
    for (const core of model.cores) {
      computations.append(h('li', { class: 'row' }, h('button', { type: 'button', class: 'row__go', onclick: () => map.select(`core:${core.id}`) },
        keyGlyph('kernel'), h('span', { class: 'row__title' }, core.id === 'replay_admission' ? 'Replay admission' : moduleWords(core.id)),
        h('span', { class: 'row__sub figures' }, `${core.id === 'replay_admission' ? 'Judges reruns' : 'Part of the toolkit'} · ${count(core.verifiedTasks || 0, 'proof check')}, ${count(core.mutants.length, 'broken version')} caught`))));
    }
    for (const k of model.kernels) {
      computations.append(h('li', { class: 'row' }, h('button', { type: 'button', class: 'row__go', onclick: () => map.select(`kernel:${k.id}`) },
        keyGlyph('kernel'), h('span', { class: 'row__title' }, proofShortName(k)),
        h('span', { class: 'row__sub figures' }, `${count(k.verifiedTasks || 0, 'proof check')}, ${count(k.mutants.length, 'broken version')} caught · in ${k.componentId ? model.byId.get(k.componentId)?.title : 'no component'}`))));
    }
    return h('div', {},
      h('div', { class: 'ledger' },
        h('div', { class: 'ledger__item' }, h('span', { class: 'ledger__n ink-ran-text' }, String(t.kernels + t.cores)), h('span', { class: 'ledger__l' }, 'computations proved with Dafny')),
        h('div', { class: 'ledger__item' }, h('span', { class: 'ledger__n ink-ran-text' }, String(t.tasks + t.coreTasks)), h('span', { class: 'ledger__l' }, 'proof checks passed, in saved results')),
        h('div', { class: 'ledger__item' }, h('span', { class: 'ledger__n' }, String(t.components)), h('span', { class: 'ledger__l' }, `components in ${count(families.length, 'family', 'families')}`)),
        h('div', { class: 'ledger__item' }, h('span', { class: 'ledger__n ink-unknown-text' }, '0'), h('span', { class: 'ledger__l' }, 'checks run live by this page'))),
      h('div', { class: 'section-head' }, h('h2', { class: 'section-title' }, 'The rings'),
        h('button', { type: 'button', class: 'textbtn', onclick: () => openExplainer() }, 'What do these mean?')),
      h('p', { class: 'small muted' }, 'Each ring is one kind of check, and each cell is one component, in the same order as the map. Hover over a row to light its ring, or click it to keep it lit.'),
      rows,
      h('p', { class: 'note' }, 'The rings overlap, so their counts don’t add up, and none of them means a whole component is proved.'),
      h('h2', { class: 'section-title' }, 'Families'),
      famRows,
      h('h2', { class: 'section-title' }, `The ${t.kernels + t.cores} proved computations`),
      h('p', { class: 'small muted' }, `Four sit at the centre and are part of the toolkit itself; the other ${t.kernels} sit inside components, on the inner ring.`),
      computations);
  }

  function filtersView() {
    const wrap = h('div', {}, h('h2', { class: 'section-title' }, 'Filters'),
      h('p', { class: 'small muted' }, 'Pick one value per filter. Filters combine with each other and with the search; the counts cover every component.'));
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
    wrap.append(h('div', { class: 'actions' }, h('button', { type: 'button', class: 'btn', onclick: () => showView('index') }, 'Show the matching list')));
    return wrap;
  }

  /* ---- Cards for a chosen object -------------------------------------------- */
  function back() {
    return h('button', { type: 'button', class: 'textbtn', onclick: () => { map.select(null); } }, '← Back to the overview');
  }
  function fact(facet, status, glyph) {
    const [text, caution, known] = stateWords(facet, status);
    return h('li', { class: `fact${known ? '' : ' fact--unknown'}` }, glyph || keyGlyph('record'),
      h('span', {}, h('span', { class: 'fact__text' }, text), caution ? h('span', { class: 'fact__caution' }, caution) : null));
  }

  // One component's column of the rings, as rows in the same inks.
  function columnFacts(c, facets) {
    const k = c.kernelId ? model.kernelById.get(c.kernelId) : null;
    const kept = c.receipts.filter((r) => r.availability === 'available');
    const dated = kept.filter((r) => r.createdAt).map((r) => r.createdAt).sort();
    const words = {
      proof: k ? `${proofShortName(k)}: ${count(k.verifiedTasks || 0, 'proof check')} passed in Dafny ${k.dafnyVersion.split('+')[0]}.` : 'No proved computation.',
      variants: k ? `${count(k.mutants.length, 'deliberately broken version')} rejected by the prover, as they should be.` : 'None.',
      bound: k ? 'The code that runs matched the proved code when this snapshot was made.' : 'None.',
      caller: k ? 'Its code calls the proved computation directly.' : 'None.',
      lean: c.checks.lean ? 'A past run saved the Lean proof checker accepting a proof. That is not a proof about this component\'s own code.' : 'None.',
      replay: c.checks.replay ? 'A rerun is set up, and the replay checker would judge it. Nothing has been rerun here.' : 'No rerun is set up.',
      saved: kept.length ? `${count(kept.length, 'past run')}${dated.length ? `, the latest on ${dayWords(dated[dated.length - 1])}` : ', dates not saved'}${c.receipts.length > kept.length ? `; ${c.receipts.length - kept.length} missing from this snapshot` : ''}.` : 'None in this snapshot.',
      whole: 'Unknown. Nobody has worked out how much of what it claims is covered.',
    };
    // Only the checks it has, each with what it found; the rest in one line.
    const list = h('ul', { class: 'column' });
    const missing = [];
    for (const t of TRACKS) {
      if (t.ink === 'unknown') continue;
      if (!c.checks[t.id]) { missing.push(t.short.toLowerCase()); continue; }
      list.append(h('li', { class: 'column__row' }, swatch(t, 'has'),
        h('span', { class: 'column__title' }, t.title), h('span', { class: 'column__by' }, t.checker),
        h('span', { class: 'column__words' }, words[t.id])));
    }
    if (facets?.host_tests?.status === 'linked_not_run') {
      list.append(h('li', { class: 'column__row' }, h('span', { class: 'swatch', style: '--ink-fill: var(--ring-caller)', 'aria-hidden': 'true' }),
        h('span', { class: 'column__title' }, 'Tests linked'), h('span', { class: 'column__by' }, 'pytest'),
        h('span', { class: 'column__words' }, 'Tests run the proved code through the component.')));
    }
    if (missing.length) list.append(h('li', { class: 'column__none' }, `Not checked this way: ${missing.join(', ')}.`));
    return list;
  }
  async function componentCard(o) {
    const c = o.comp;
    const mine = ++cardRun;
    const column = h('div', {}, columnFacts(c, null));
    const card = h('div', {}, back(),
      h('p', { class: 'card-kind', style: 'margin-top:0.9rem' }, backingGlyph(c.backing, c.kernelId ? 'mark--proved' : 'mark'), `${classWords('evidence_class', c.evidenceClass)} · ${familyName(c.family)}`),
      h('h2', { class: 'card-title' }, c.title),
      h('p', { class: 'card-plain', 'data-plain': '' }, c.summary),
      h('h3', { class: 'section-title' }, 'What checks it'), column,
      h('div', { class: 'limit', 'data-limit': '' }, h('span', { class: 'limit__label' }, 'What it does not claim'), 'Loading…'),
      h('details', { class: 'fullwriteup', open: true }, h('summary', {}, 'Full write-up'), h('div', { 'data-writeup': '' }, h('p', { class: 'muted small' }, 'Loading the write-up…'))));
    loadPlain('component', c.id).then((text) => {
      if (text && mine === cardRun && !destroyed) card.querySelector('[data-plain]').textContent = text;
    });
    loadWriteup('component', c.id, model.links, { skipPlain: true }).then((el) => {
      if (mine === cardRun && !destroyed) card.querySelector('[data-writeup]').replaceChildren(el);
    });
    if (c.kernelId) {
      const k = model.kernelById.get(c.kernelId);
      card.append(h('h3', { class: 'section-title' }, `Its proved part: ${proofShortName(k)}`),
        h('p', { class: 'statement' }, k.statement),
        h('div', { class: 'actions' },
          h('button', { type: 'button', class: 'btn btn--ink', onclick: () => map.select(`kernel:${k.id}`) }, 'See the proof'),
          h('a', { class: 'btn', href: `/proofs/${encodeURIComponent(k.id)}`, 'data-route': '' }, 'Open the proof page')));
    }
    card.append(h('h3', { class: 'section-title' }, `Past runs (${c.receipts.length})`),
      runsStrip(c.receipts, model.source),
      h('p', { class: 'note' }, 'Newest first. These are saved results of earlier runs; this page does not rerun them.'));
    const doctrine = c.doctrineIds.map((id) => model.doctrine.get(id)).filter(Boolean);
    if (doctrine.length) {
      card.append(h('h3', { class: 'section-title' }, 'Principles it cites'),
        h('ul', { class: 'doctrine' }, doctrine.map((d) => h('li', {}, h('span', { class: `doc-id doc-id--${d.kind}` }, d.id), ' ', h('strong', {}, d.title),
          h('span', { class: 'muted small' }, ` ${d.kind === 'anti_principle' ? 'Failure mode' : d.kind === 'axiom' ? 'Axiom' : 'Principle'}`)))));
    }
    const wired = model.wires.filter(([a, b]) => a === c.id || b === c.id).map(([a, b]) => (a === c.id ? b : a));
    const imports = [...c.importsOut.map((e) => [e.to, e]), ...c.importsIn.map((e) => [e.from, e])];
    if (wired.length || imports.length) {
      const list = h('ul', { class: 'rows' });
      for (const [id, e] of imports) {
        const other = model.byId.get(id);
        if (!other) continue;
        list.append(h('li', { class: 'row' }, h('button', { type: 'button', class: 'row__go', onclick: () => map.select(`comp:${id}`) },
          backingGlyph(other.backing, other.kernelId ? 'mark--proved' : 'mark'), h('span', { class: 'row__title' }, other.title),
          h('span', { class: 'row__sub' }, e.from === c.id ? 'Its code imports this one' : 'This one\'s code imports it'))));
      }
      for (const id of wired) {
        const other = model.byId.get(id);
        list.append(h('li', { class: 'row' }, h('button', { type: 'button', class: 'row__go', onclick: () => map.select(`comp:${id}`) },
          backingGlyph(other.backing, other.kernelId ? 'mark--proved' : 'mark'), h('span', { class: 'row__title' }, other.title),
          h('span', { class: 'row__sub' }, `Declared connection · ${familyName(other.family)}`))));
      }
      card.append(h('h3', { class: 'section-title' }, `Connections (${wired.length + imports.length})`),
        h('p', { class: 'note' }, 'Connections declared in the source code. They say these components are meant to work together, not that one has called the other.'), list);
    }
    card.append(h('div', { class: 'actions' },
      h('a', { class: 'btn btn--ink', href: `/components/${encodeURIComponent(c.id)}`, 'data-route': '' }, 'Open the component page'),
      h('a', { class: 'btn', href: withQuery('/graph', { type: 'organ', id: c.id }), 'data-route': '' }, 'Related records')));
    clear(body).append(card);
    body.scrollTop = 0;
    let detail;
    try {
      detail = (await getEnvelope(apiPath('components', c.id))).data;
    } catch (error) {
      if (mine !== cardRun) return;
      card.querySelector('[data-limit]').replaceChildren(h('span', { class: 'limit__label' }, 'What it does not claim'), `This component's details could not be loaded: ${error.message}`);
      return;
    }
    if (mine !== cardRun || destroyed) return;
    const claim = detail.claim || {};
    const facets = claim.card?.assurance_facets || {};
    card.querySelector('[data-limit]').replaceChildren(h('span', { class: 'limit__label' }, 'What it does not claim'), claim.claim_ceiling_restated || claim.claim_ceiling || 'No limit is written down.');
    column.replaceChildren(columnFacts(c, facets));
  }

  function proofFacts(p) {
    return h('ul', { class: 'facts' },
      h('li', { class: 'fact' }, keyGlyph('task'), h('span', {}, `Dafny ${p.dafnyVersion.split('+')[0] || ''} passed ${count(p.verifiedTasks || 0, 'proof check')}.`, h('span', { class: 'fact__caution' }, 'A saved result from when the proof was last run; this page does not run the prover.'))),
      h('li', { class: 'fact' }, keyGlyph('variant'), h('span', {}, `${count(p.mutants.length, 'deliberately broken version')} failed the proof, as they should.`)),
      fact('proof_binding', p.binding, keyGlyph('generated')),
      fact('fresh_prover', p.freshProver, keyGlyph('absent')),
      fact('requirements_review', p.requirementsReview, keyGlyph('absent')));
  }

  function kernelCard(o) {
    const k = o.kernel;
    const comp = o.componentId ? model.byId.get(o.componentId) : null;
    const isOwnership = model.ownership && model.ownership.proof_id === k.id;
    clear(body).append(h('div', {}, back(),
      h('p', { class: 'card-kind', style: 'margin-top:0.9rem' }, keyGlyph('kernel'), comp ? `Proved computation inside ${comp.title}` : 'Proved computation'),
      h('h2', { class: 'card-title' }, proofShortName(k)),
      h('p', { class: 'card-plain' }, flowerWords(k, comp ? `It makes one decision inside “${comp.title}”.` : '')),
      h('h3', { class: 'section-title' }, 'The exact promise'),
      h('p', { class: 'statement' }, k.statement),
      h('div', { class: 'limit' }, h('span', { class: 'limit__label' }, 'What the proof leaves out'), k.limits || 'No limit is written down.'),
      isOwnership ? h('div', {}, h('h3', { class: 'section-title' }, 'Why the requirement mattered'), ownershipFigure(model.ownership, model.source)) : null,
      h('h3', { class: 'section-title' }, 'The written rules, in Dafny'),
      specificationParts(k, model.source),
      h('h3', { class: 'section-title' }, 'Broken versions the prover rejected'),
      variantsPart(k, model.source),
      h('h3', { class: 'section-title' }, 'What is checked, and what is not'),
      proofFacts(k),
      h('h3', { class: 'section-title' }, 'What it takes in'), h('p', { class: 'small' }, k.inputModel),
      h('h3', { class: 'section-title' }, 'Assumptions'), h('p', { class: 'small' }, k.assumptions),
      h('div', { class: 'actions' },
        h('a', { class: 'btn btn--ink', href: `/proofs/${encodeURIComponent(k.id)}`, 'data-route': '' }, 'Open the proof page'),
        comp ? h('button', { type: 'button', class: 'btn', onclick: () => map.select(`comp:${comp.id}`) }, `Its component: ${comp.title}`) : null)));
    body.scrollTop = 0;
  }

  function coreCard(o) {
    const c = o.core;
    const centre = c.id === 'replay_admission';
    const wrap = h('div', {}, back(),
      h('p', { class: 'card-kind', style: 'margin-top:0.9rem' }, keyGlyph('kernel'), centre ? 'At the centre: the replay checker' : 'Part of the toolkit itself'),
      h('h2', { class: 'card-title' }, CORE_NAMES[c.id]?.[0] || moduleWords(c.id)),
      h('p', { class: 'card-plain' }, flowerWords(c, `It ${CORE_NAMES[c.id]?.[1] || 'is part of the toolkit'}, and the toolkit calls it directly.`)),
      h('h3', { class: 'section-title' }, 'The exact promise'),
      h('p', { class: 'statement' }, c.statement),
      h('div', { class: 'limit' }, h('span', { class: 'limit__label' }, 'What the proof leaves out'), c.limits || 'No limit is written down.'),
      h('h3', { class: 'section-title' }, 'What is checked, and what is not'),
      proofFacts(c),
      h('h3', { class: 'section-title' }, 'Assumptions'), h('p', { class: 'small' }, c.assumptions),
      h('div', { 'data-writeup': '' }),
      h('h3', { class: 'section-title' }, 'Who calls it'),
      h('ul', { class: 'callers' }, c.callers.map((ref) => {
        const { api, fn } = callerWords(ref);
        const href = sourceHref(model.source, ref);
        const inner = [h('strong', {}, api), fn ? h('span', { class: 'muted' }, ` · ${fn.replace(/_/g, ' ')}`) : null];
        return h('li', {}, href ? h('a', { href, rel: 'noopener', target: '_blank' }, inner) : inner);
      })),
      h('h3', { class: 'section-title' }, 'Broken versions the prover rejected'),
      variantsPart(c, model.source));
    if (centre && c.admitted.length) {
      const list = h('ul', { class: 'rows rows--dense' });
      for (const a of c.admitted) {
        const comp = model.byId.get(a.componentId);
        list.append(h('li', { class: 'row' }, h('button', { type: 'button', class: 'row__go', onclick: () => map.select(`comp:${a.componentId}`) },
          comp ? backingGlyph(comp.backing, comp.kernelId ? 'mark--proved' : 'mark') : keyGlyph('absent'),
          h('span', { class: 'row__title' }, comp ? comp.title : a.componentId), h('code', { class: 'row__sub' }, a.route))));
      }
      wrap.append(h('h3', { class: 'section-title' }, `The ${c.admitted.length} reruns it would judge`),
        h('p', { class: 'note' }, 'One per component, drawn as the blue spokes. It accepts a rerun only if every component is covered and each result matches what was saved. Nothing has been rerun here.'), list);
    }
    clear(body).append(wrap);
    body.scrollTop = 0;
    const run = ++cardRun;
    loadWriteup('core', c.id, model.links).then((el) => {
      if (run === cardRun && !destroyed && el.classList.contains('writeup')) wrap.querySelector('[data-writeup]').replaceChildren(h('h3', { class: 'section-title' }, 'Its write-up'), el);
    });
  }

  function onSelect(o) {
    peek.classList.remove('is-on');
    const hash = o ? `#o=${encodeURIComponent(o.key)}` : '';
    history.replaceState(null, '', `${window.location.pathname}${window.location.search}${hash}`);
    if (!o) { showView(panelView === 'card' ? 'overview' : panelView); return; }
    panelView = 'card';
    for (const b of [tabOverview, tabIndex, utilFilters, utilKey]) press(b, false);
    explorer.dispatchEvent(new CustomEvent('explorer:selected', { bubbles: true }));
    if (o.type === 'component') { componentCard(o); announce(`${o.comp.title} selected`); }
    else if (o.type === 'kernel') { kernelCard(o); announce(`${proofShortName(o.kernel)} kernel selected`); }
    else if (o.type === 'core') { coreCard(o); announce(`${o.core.id === 'replay_admission' ? 'Replay admission' : moduleWords(o.core.id)} core selected`); }
  }

  /* ---- Boot ----------------------------------------------------------------- */
  showView(state.q ? 'index' : 'overview');
  syncFiltered();
  try {
    model = await getModel();
    setLabels(model.filters);
  } catch (error) {
    if (destroyed) return () => {};
    status.replaceChildren(errorBlock(error, () => navigate(window.location.href, { replace: true })));
    foot.textContent = '';
    return () => { destroyed = true; unwire(); document.removeEventListener('keydown', slashFocus); };
  }
  if (destroyed) return () => {};
  status.hidden = true;
  const src = model.source ? `, built from commit ${model.source.commit.slice(0, 10)}` : '';
  foot.textContent = `Snapshot ${model.revision.slice(0, 12)}${src}.`;
  foot.title = model.revision;
  const t = model.totals;
  lede.textContent = `Plectis has ${t.components} components. For ${t.kernels + t.cores} small computations in it, a tool called Dafny has proved that the code follows written rules, and the proved code is the code that runs. The rings around the map show what else checks each component, and the gaps show what nothing checks.`;
  if (revealPlayed) document.documentElement.classList.add('map-seen');
  let peekTimer = 0, peekKey = null;
  function showPeek(o) {
    clearTimeout(peekTimer);
    const key = o && (o.type === 'component' || o.type === 'kernel' || o.type === 'core') && o.key !== map?.selectedKey() ? o.key : null;
    if (key === peekKey) return;
    peekTimer = setTimeout(() => {
      peekKey = key;
      if (!key) { peek.classList.remove('is-on'); return; }
      peek.replaceChildren(peekCard(o));
      peek.classList.add('is-on');
    }, key ? 70 : 160);
  }
  function peekCard(o) {
    if (o.type === 'component') {
      const c = o.comp;
      const text = h('p', { class: 'peek__plain' }, c.summary);
      loadPlain('component', c.id).then((plain) => { if (plain && peekKey === o.key) text.textContent = plain; });
      return h('div', {},
        h('p', { class: 'card-kind' }, backingGlyph(c.backing, c.kernelId ? 'mark--proved' : 'mark'), familyName(c.family)),
        h('p', { class: 'peek__title' }, c.title),
        text,
        h('div', { class: 'peek__checks', 'aria-hidden': 'true' }, TRACKS.map((t) => h('span', { class: 'peek__check', title: t.title },
          swatch(t, t.ink === 'unknown' ? 'unknown' : c.checks[t.id] ? 'has' : 'empty')))),
        h('p', { class: 'peek__hint' }, 'Click to read more'));
    }
    const p = o.type === 'kernel' ? o.kernel : o.core;
    const name = o.type === 'kernel' ? proofShortName(p) : CORE_NAMES[o.core.id]?.[0] || moduleWords(o.core.id);
    const comp = o.type === 'kernel' && o.componentId ? model.byId.get(o.componentId) : null;
    const usedBy = o.type === 'kernel' ? (comp ? `It makes one decision inside “${comp.title}”.` : '') : `It ${CORE_NAMES[o.core.id]?.[1] || 'is part of the toolkit'}.`;
    return h('div', {},
      h('p', { class: 'card-kind' }, keyGlyph('kernel'), o.type === 'kernel' ? 'Proved computation inside a component' : 'Proved computation in the toolkit'),
      h('p', { class: 'peek__title' }, name),
      h('p', { class: 'peek__plain' }, flowerWords(p, usedBy)),
      h('p', { class: 'peek__hint' }, 'Click to see the exact rules and the proof.'));
  }

  map = createMap(canvas, model, {
    onHover: showPeek,
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
  if (panelView === 'overview') showView('overview');
  const wanted = decodeURIComponent((window.location.hash.match(/^#o=(.+)$/) || [])[1] || '');
  if (wanted && map.objectFor(wanted)) map.select(wanted);
  // Read every write-up in the background, a few at a time, so pointing at
  // a component shows its plain description at once.
  // It starts after the opening has drawn, so it never delays the map.
  setTimeout(async () => {
    const ids = model.components.map((c) => c.id);
    for (let i = 0; i < ids.length && !destroyed; i += 3) await Promise.all(ids.slice(i, i + 3).map((id) => fetchWriteup('component', id)));
  }, 2600);

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
    box.append(h('strong', {}, 'The data server is not running. '), 'From the repository, start the explorer with ', h('code', {}, 'make explorer'), ' and reload.');
  } else if (error.kind === 'schema') {
    box.append(h('strong', {}, 'The API answered with a contract this explorer does not read. '), error.message);
  } else if (error.kind === 'not_found') {
    box.append(h('strong', {}, 'This data server is older than the explorer. '), 'Start both from this repository with ', h('code', {}, 'make explorer'), '.');
  } else if (error.kind === 'revision') {
    box.append(h('strong', {}, 'The component index changed twice while loading. '), 'Nothing from the two snapshots was combined.');
  } else {
    box.append(h('strong', {}, 'The map could not be loaded. '), error.message);
  }
  box.append(' ', h('button', { type: 'button', class: 'textbtn', onclick: retry }, 'Try again'));
  return box;
}
