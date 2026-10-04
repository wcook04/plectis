import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import vm from 'node:vm';

const HOT_EDGE = '#13579b';
const source = readFileSync(new URL('../../../tools/meta/dissemination/maths_site_assets/universe.js', import.meta.url), 'utf8');

function element(attrs = {}) {
  const events = {};
  const classes = new Set();
  return {
    innerHTML: '', textContent: '', value: '', disabled: false, hidden: false,
    getAttribute: name => attrs[name] ?? null,
    setAttribute: (name, value) => { attrs[name] = value; },
    contains: () => false, focus() {}, select() {},
    querySelector: () => null,
    classList: { contains: name => classes.has(name), add: name => classes.add(name),
      remove: name => classes.delete(name), toggle(name, on) { on ? classes.add(name) : classes.delete(name); } },
    addEventListener(name, fn) { (events[name] ||= []).push(fn); },
    fire(name, event = {}) {
      const dispatched = {preventDefault() {}, stopPropagation() {}, ...event};
      for (const fn of events[name] || []) fn(dispatched);
    },
  };
}

async function mount(options = {}) {
  let arcs = [], strokes = [], labels = [], path = [], pen, dash = [];
  const context = new Proxy({
    clearRect() { arcs = []; strokes = []; labels = []; },
    beginPath() { path = []; pen = null; },
    moveTo(x, y) { pen = [x, y]; },
    lineTo(x, y) {
      if (pen) path.push({from: pen, to: [x, y]});
      pen = [x, y];
    },
    setLineDash(segments) { dash = segments; },
    stroke() {
      strokes.push({style: context.strokeStyle, alpha: context.globalAlpha, dashed: dash.length > 0, segments: path.slice()});
    },
    arc(x, y, r) { arcs.push({x, y, r}); },
    measureText(text) { return {width: String(text).length * 6}; },
    fillText(text, x, y) { labels.push({text, x, y, alpha: context.globalAlpha}); },
  }, { get: (target, key) => target[key] ?? (() => {}) });
  const canvas = Object.assign(element({'data-universe-src': 'initial', ...(options.attrs || {})}), {
    clientWidth: options.width ?? 292, clientHeight: 340, getContext: () => context,
    getBoundingClientRect: () => ({left: 0, top: 0, bottom: 340}),
  });
  canvas.classList.add('universe-canvas--page');
  const count = element();
  const inspector = element();
  const scrolled = [];
  if (options.inspectorTop != null) {
    Object.assign(inspector, {getBoundingClientRect: () => ({top: options.inspectorTop}),
      scrollIntoView: opts => { scrolled.push(opts); }});
  }
  const search = element();
  search.value = options.searchValue ?? '';
  const modules = element({'data-universe-lens': 'lean_module', 'aria-pressed': 'true'});
  const claims = element({'data-universe-lens': 'public_claim', 'aria-pressed': 'true'});
  const zoom = element({'data-universe-zoom': 'out'});
  const fit = element({'data-universe-zoom': 'fit'});
  const full = element({'data-graph-src': 'graph', 'data-layout-src': 'layout'});
  const stage = Object.assign(element(), {
    querySelector: s => s === 'canvas' ? canvas : null,
    querySelectorAll: s => s === '[data-universe-zoom]' ? [zoom, fit] : [],
  });
  const selectors = {'[data-universe-inspector]': inspector, '[data-universe-count]': count,
    '[data-universe-search]': search, '[data-universe-load-full]': full};
  const document = Object.assign(element(), {
    readyState: 'complete', documentElement: element(), activeElement: null,
    querySelector: s => selectors[s] || null,
    querySelectorAll: s => s === '[data-universe-stage]' ? [stage] : s === '[data-universe-lens]' ? [claims, modules] : [],
  });
  const location = {pathname: '/maths/universe.html', search: '', hash: options.hash ?? ''};
  const window = Object.assign(element(), {
    location, devicePixelRatio: 1, isSecureContext: false, innerHeight: 664,
    history: {replaceState(_a, _b, url) { location.hash = new URL(url, 'http://test').hash; }},
  });
  const nodes = [
    {id: 'problem:one', kind: 'problem', label: 'First problem', x: -500, y: 0},
    {id: 'problem:two', kind: 'problem', label: 'Second problem', x: 500, y: 0},
    {id: 'claim:one', kind: 'public_claim', label: 'One checked claim', x: 0, y: 100},
  ];
  const module = {id: 'lean-module:Deep', kind: 'lean_module', label: 'Deep module'};
  const requests = [];
  const data = options.data ?? {
    initial: {nodes, edges: [[0, 2], [1, 2], [0, 1]]},
    graph: {nodes: [...nodes, module], edges: [{source: module.id, target: nodes[0].id}]},
    layout: {positions: Object.fromEntries([...nodes, {...module, x: 0, y: 200}].map(n => [n.id, [n.x, n.y]]))},
  };
  const timers = [];
  const flushTimers = () => { for (const fn of timers.splice(0)) fn(); };
  vm.runInNewContext(source, {document, window, navigator: {},
    getComputedStyle: () => ({getPropertyValue: name => name === '--u-edge-hot' ? HOT_EDGE : ''}),
    fetch: async url => { requests.push(url); return {json: async () => data[url]}; },
    setTimeout: fn => { if (options.queueTimers) timers.push(fn); else fn(); return 1; }, clearTimeout() {},
  });
  const settle = () => new Promise(resolve => setImmediate(resolve));
  await settle();
  return {canvas, count, inspector, search, claims, modules, zoom, fit, full, location, window, scrolled,
    document, requests, settle, flushTimers, arcs: () => arcs, strokes: () => strokes, labels: () => labels,
    drawnSegments: () => strokes.flatMap(stroke => stroke.segments),
    dashedSegments: () => strokes.filter(stroke => stroke.dashed).flatMap(stroke => stroke.segments),
    hotSegments: () => strokes.filter(stroke => stroke.style === HOT_EDGE).flatMap(stroke => stroke.segments),
    span: () => Math.max(...arcs.map(a => a.x)) - Math.min(...arcs.map(a => a.x)),
  };
}

test('zoom out shrinks a map already fitted below the desktop zoom floor', async () => {
  const map = await mount();
  const before = map.span();
  map.zoom.fire('click');
  assert.ok(map.span() < before);
  for (let i = 0; i < 10; i++) map.zoom.fire('click');
  assert.ok(map.span() > 0, 'zoom stays bounded');
});

test('filter feedback says plainly how many objects are shown, and draws only links between them', async () => {
  const map = await mount();
  assert.equal(map.count.textContent, '3 shown');
  assert.equal(map.drawnSegments().length, 3);
  map.claims.fire('click');
  assert.equal(map.count.textContent, '2 of 3 shown');
  assert.equal(map.drawnSegments().length, 1, 'only the link whose two ends remain visible is drawn');
  map.claims.fire('click');
  assert.equal(map.count.textContent, '3 shown');
  assert.equal(map.drawnSegments().length, 3);
});

test('resizing preserves an explored scale instead of refitting the graph', async () => {
  const map = await mount();
  map.zoom.fire('click');
  const before = map.span();
  map.canvas.clientWidth = 500;
  map.window.fire('resize');
  assert.ok(Math.abs(map.span() - before) < 1e-9);
});

test('the shared claim band stays named in a fitted phone view with another programme pinned', async () => {
  const data = {initial: {
    nodes: [
      {id: 'universe:all', kind: 'universe', label: 'Universe', x: 0, y: 0},
      {id: 'problem:erdos_68', kind: 'problem', label: 'Programme 68', x: 0, y: -320},
      {id: 'problem:erdos_249', kind: 'problem', label: 'Programme 249', x: 320, y: 0},
      {id: 'problem:erdos_257', kind: 'problem', label: 'Programme 257', x: 0, y: 320},
      {id: 'claim:shared', kind: 'public_claim', label: 'Shared claim', x: 250, y: 250},
    ],
    edges: [[0, 1], [0, 2], [0, 3], [0, 4]],
    captions: [{x: 145, y: 145, text: 'shared by #249 and #257', sub: '74 claims in one Lean namespace'}],
  }};
  const map = await mount({data, hash: '#o=problem%3Aerdos_68'});
  map.fit.fire('click');
  const label = map.labels().find(mark => mark.text === 'Shared: #249 and #257');
  assert.ok(label, 'the fitted view identifies both programmes even when neither is selected');
  assert.ok(label.alpha >= 0.8, 'an unrelated pin does not make the label unreadable');
  assert.ok(label.x >= 0 && label.x <= map.canvas.clientWidth && label.y >= 0 && label.y <= map.canvas.clientHeight);
  assert.ok(label.x + label.text.length * 3 <= map.canvas.clientWidth - 74,
    'the whole caption stays outside the zoom control column');
  assert.match(map.inspector.innerHTML, /Programme 68/);
  assert.equal(map.location.hash, '#o=problem%3Aerdos_68');
});

test('a name plate over the shared callout makes the callout step aside, not show through', async () => {
  // Without statement bands the callout sits 2.35 times the caption's radius
  // out along its spoke, so a claim on that spot names itself across it.
  const caption = {x: 145, y: 145, text: 'shared by #249 and #257', sub: '74 claims in one Lean namespace'};
  const data = () => ({initial: {
    nodes: [
      {id: 'universe:all', kind: 'universe', label: 'Universe', x: 0, y: 0},
      {id: 'problem:erdos_249', kind: 'problem', label: 'Programme 249', x: 320, y: 0},
      {id: 'problem:erdos_257', kind: 'problem', label: 'Programme 257', x: 0, y: 320},
      {id: 'claim:edge', kind: 'public_claim', label: 'Claim on the edge', x: caption.x * 2.35, y: caption.y * 2.35},
    ],
    edges: [[0, 1], [0, 2], [0, 3]],
    captions: [caption],
  }});
  const SHARED = 'Shared: #249 and #257';
  const plain = await mount({data: data(), width: 900});
  plain.fit.fire('click');
  const callout = plain.labels().find(mark => mark.text === SHARED);
  assert.ok(callout, 'with nothing in focus the fitted view names the shared block');
  const hangsOnCallout = s => s.to[0] === callout.x && s.to[1] === callout.y - 8;
  assert.ok(plain.dashedSegments().some(hangsOnCallout), 'the callout hangs on its dashed line');

  const pinned = await mount({data: data(), width: 900, hash: '#o=claim%3Aedge'});
  pinned.fit.fire('click');
  const name = pinned.labels().find(mark => mark.text === 'Claim on the edge');
  assert.ok(name, 'the pinned claim names itself on a plate');
  // The fake face sets six pixels a letter; the plate pads its text by nine.
  const plateHalf = name.text.length * 3 + 9, calloutHalf = SHARED.length * 3 + 6;
  assert.ok(Math.abs(name.x - callout.x) < plateHalf + calloutHalf &&
    callout.y + 8 > name.y - 16 && callout.y - 8 < name.y + 7,
    'the plate lies across the place the callout takes');
  assert.ok(!pinned.labels().some(mark => mark.text === SHARED),
    'the callout steps aside under the plate instead of showing through it');
  assert.ok(!pinned.dashedSegments().some(hangsOnCallout), 'its line goes with it');
});

test('a deep object hash loads the full corpus and takes precedence over the old pin', async () => {
  const map = await mount();
  map.search.value = 'First';
  map.search.fire('input');
  map.search.fire('keydown', {key: 'Enter'});
  assert.equal(map.location.hash, '#o=problem%3Aone');
  map.location.hash = '#o=lean-module%3ADeep';
  map.window.fire('hashchange');
  map.window.fire('hashchange');
  await map.settle();
  assert.match(map.inspector.innerHTML, /Deep module/);
  assert.equal(map.location.hash, '#o=lean-module%3ADeep');
  assert.equal(map.requests.filter(url => url === 'graph').length, 1, 'concurrent hashes share the load');
});

function hierarchyFixture() {
  const core = {id: 'universe:all', kind: 'universe', label: 'Universe', x: 0, y: 0};
  const anchors = [
    {id: 'problem:east', kind: 'problem', label: 'East problem', x: 130, y: -70},
    {id: 'problem:west', kind: 'problem', label: 'West problem', x: -130, y: -70},
  ];
  const claim = {id: 'claim:checked', kind: 'public_claim', label: 'Checked claim', x: 80, y: 70};
  const modules = Array.from({length: 96}, (_, i) => ({
    id: `lean-module:Fan${String(i).padStart(2, '0')}`, kind: 'lean_module',
    label: `Fan module ${String(i).padStart(2, '0')}`,
    x: 90 * Math.cos(i * Math.PI / 48), y: 90 * Math.sin(i * Math.PI / 48),
  }));
  const nodes = [core, ...anchors, claim, ...modules];
  const edges = [
    ...anchors.map(n => ({source: core.id, target: n.id, relation: 'contains'})),
    ...modules.map(n => ({source: core.id, target: n.id, relation: 'contains'})),
    {source: modules[0].id, target: claim.id, relation: 'proves'},
    {source: modules[0].id, target: modules[1].id, relation: 'imports'},
  ];
  return {
    initial: {nodes: [core, ...anchors, claim], edges: [[0, 1], [0, 2]]},
    graph: {nodes, edges},
    layout: {positions: Object.fromEntries(nodes.map(n => [n.id, [n.x, n.y]]))},
  };
}

async function fullHierarchy(options = {}) {
  const map = await mount({data: hierarchyFixture(), ...options});
  map.full.fire('click');
  await map.settle();
  assert.equal(map.full.textContent, 'Complete universe loaded');
  return map;
}

test('a narrow Universe selection keeps anchors without lighting the containment fan', async () => {
  const map = await fullHierarchy();
  assert.equal(map.count.textContent, '100 shown');
  assert.equal(map.drawnSegments().length, 2, 'overview omits every global module edge');
  // Click the rendered core at the fitted canvas centre: no test calls an
  // internal selector or reimplements the renderer's edge classification.
  const core = map.arcs().reduce((largest, arc) => arc.r > largest.r ? arc : largest);
  map.canvas.fire('click', {clientX: core.x, clientY: core.y});
  assert.equal(map.location.hash, '#o=universe%3Aall');
  assert.match(map.inspector.innerHTML, /How it connects/);
  assert.equal((map.inspector.innerHTML.match(/data-universe-go=/g) || []).length, 98, 'every adjacency remains reachable in the inspector');
  assert.match(map.inspector.innerHTML, /Fan module 95/, 'the last containment entry is not truncated');
  const moduleGroup = [...map.inspector.innerHTML.matchAll(/<details([^>]*)><summary>(.*?)<\/summary>/g)]
    .find(([, , title]) => /\d+ lean modules$/.test(title));
  assert.ok(moduleGroup, 'module adjacency is grouped behind a disclosure');
  assert.doesNotMatch(moduleGroup[1], /\bopen\b/, 'the dense module group starts collapsed');
  const hot = map.hotSegments();
  assert.equal(hot.length, 2, 'only the two overview anchors are highlighted, not 96 module spokes');
  assert.equal(map.drawnSegments().length, 2);
  assert.equal(map.count.textContent, '100 shown');
  for (const anchor of ['Universe', 'East problem', 'West problem']) {
    assert.ok(map.labels().some(label => label.text === anchor), `${anchor} remains labelled`);
  }
});

test('a full-corpus module keeps its incident links through hash, search and lenses', async () => {
  const map = await mount({data: hierarchyFixture(), hash: '#o=lean-module%3AFan00'});
  await map.settle();
  assert.equal(map.requests.filter(url => url === 'graph').length, 1);
  assert.match(map.inspector.innerHTML, /Fan module 00/);
  assert.match(map.inspector.innerHTML, /How it connects/);
  assert.equal(map.hotSegments().length, 3, 'module containment, proof and import are all drawn');
  assert.equal(map.drawnSegments().length, 5, 'two anchors remain in the background');
  assert.equal(map.count.textContent, '100 shown');
  assert.ok(map.hotSegments().every(segment => segment.from.every(Number.isFinite) && segment.to.every(Number.isFinite)));

  map.search.value = 'Fan module 95';
  map.search.fire('input');
  assert.match(map.count.textContent, /, 1 found$/);
  map.search.fire('keydown', {key: 'Enter'});
  assert.equal(map.location.hash, '#o=lean-module%3AFan95');
  assert.match(map.inspector.innerHTML, /Fan module 95/);
  assert.equal(map.hotSegments().length, 1, 'the last module in the complete corpus remains selectable');
  map.search.fire('keydown', {key: 'Escape'});
  assert.equal(map.count.textContent, '100 shown');
  assert.equal(map.drawnSegments().length, 3);

  map.modules.fire('click');
  assert.equal(map.location.hash, '', 'hiding the selected kind clears its pin');
  assert.equal(map.count.textContent, '4 of 100 shown');
  assert.equal(map.drawnSegments().length, 2);
  assert.equal(map.hotSegments().length, 0);
  map.modules.fire('click');
  assert.equal(map.count.textContent, '100 shown');
  assert.equal(map.drawnSegments().length, 2);
  map.location.hash = '#o=lean-module%3AFan00';
  map.window.fire('hashchange');
  assert.equal(map.hotSegments().length, 3);
  map.claims.fire('click');
  assert.equal(map.count.textContent, '99 of 100 shown');
  assert.equal(map.drawnSegments().length, 4);
  assert.equal(map.hotSegments().length, 2, 'hidden claim removes exactly its incident proof link');
  map.claims.fire('click');
  assert.equal(map.count.textContent, '100 shown');
  assert.equal(map.drawnSegments().length, 5);
  assert.equal(map.hotSegments().length, 3);
});

test('Universe search and deep hash retain all eight programme anchors in the fitted view', async () => {
  const anchors = Array.from({length: 8}, (_, i) => ({
    id: `problem:${101 + i}`, kind: 'problem', label: `Erdős problem #${101 + i}`,
    short: `#${101 + i}`, x: 130 * Math.cos(i * Math.PI / 4), y: 90 * Math.sin(i * Math.PI / 4),
  }));
  const data = {initial: {
    nodes: [{id: 'universe:all', kind: 'universe', label: 'Universe', x: 0, y: 0}, ...anchors],
    edges: anchors.map((_, i) => [0, i + 1]),
  }};
  const map = await mount({data, hash: '#o=universe%3Aall'});
  const fittedSpan = map.span();
  assert.ok(fittedSpan <= map.canvas.clientWidth - 70, 'root hash leaves the entire programme fitted');
  map.search.value = 'Universe';
  map.search.fire('input');
  map.search.fire('keydown', {key: 'Enter'});
  assert.equal(map.location.hash, '#o=universe%3Aall');
  assert.equal(map.hotSegments().length, 8);
  for (let i = 0; i < 8; i++) {
    const label = map.labels().find(mark => mark.text === `#${101 + i}`);
    assert.ok(label, `programme #${101 + i} remains labelled while searching Universe`);
    assert.ok(label.x >= 0 && label.x <= map.canvas.clientWidth && label.y >= 0 && label.y <= map.canvas.clientHeight);
    assert.ok(label.alpha >= 0.7, 'programme label remains legible');
  }
  assert.equal(map.span(), fittedSpan, 'searching the root does not magnify the programme out of view');
});

test('dense module focus bounds actual strokes at phone and desktop sizes', async () => {
  const claims = Array.from({length: 30}, (_, i) => ({
    id: `claim:${i}`, kind: 'public_claim', label: `Claim ${String(i).padStart(2, '0')}`,
    x: (i + 1) * 10, y: 50,
  }));
  const data = {initial: {
    nodes: [{id: 'lean-module:hub', kind: 'lean_module', label: 'Dense module', x: 0, y: 0}, ...claims,
      {id: 'problem:anchor', kind: 'problem', label: 'Programme anchor', x: -20, y: -40}],
    // Reversed ingestion order must not decide which neighbours can be read.
    edges: [...claims.map((_, i) => [0, 30 - i]), [0, 31]],
  }};
  for (const [width, cap] of [[292, 12], [599, 12], [600, 24], [800, 24]]) {
    const map = await mount({width, data, hash: '#o=lean-module%3Ahub'});
    assert.match(map.inspector.innerHTML, /How it connects/);
    assert.equal((map.inspector.innerHTML.match(/data-universe-go=/g) || []).length, 31, 'canvas cap does not truncate navigable adjacency');
    const hot = map.hotSegments();
    assert.equal(hot.length, cap, `actual focused strokes are bounded at ${width}px`);
    assert.equal(map.drawnSegments().length, cap);
    assert.equal(map.count.textContent, '32 shown');
    const endpointXs = hot.map(segment => segment.to[0]);
    assert.ok(endpointXs[0] < hot[0].from[0], 'the problem anchor takes priority over claims ingested earlier');
    assert.deepEqual(endpointXs, endpointXs.slice().sort((a, b) => a - b), 'label order wins over reversed edge ingestion');
    const step = endpointXs[2] - endpointXs[1];
    assert.ok(Math.abs(endpointXs[1] - hot[1].from[0] - step) < 1e-9, 'the first named claim starts the bounded set');
    assert.ok(Math.abs(endpointXs.at(-1) - hot.at(-1).from[0] - (cap - 1) * step) < 1e-9);
  }
});

test('loading the complete corpus preserves an explored camera, pin and lens', async () => {
  const map = await mount();
  map.claims.fire('click');
  map.search.value = 'First';
  map.search.fire('input');
  map.search.fire('keydown', {key: 'Enter'});
  map.zoom.fire('click');
  const before = map.span();
  map.full.fire('click');
  await map.settle();
  assert.equal(map.location.hash, '#o=problem%3Aone');
  assert.match(map.inspector.innerHTML, /First problem/);
  assert.equal(map.claims.getAttribute('aria-pressed'), 'false');
  assert.equal(map.count.textContent, '3 of 4 shown, 1 found');
  assert.ok(Math.abs(map.span() - before) < 1e-9, 'full loading leaves the existing world-to-canvas scale intact');
});

test('overview retains semantic edges while root-to-claim spokes stay quiet', async () => {
  const data = {initial: {
    nodes: [
      {id: 'universe:all', kind: 'universe', label: 'Universe', x: 0, y: 0},
      {id: 'problem:one', kind: 'problem', label: 'Programme', x: -100, y: 50},
      {id: 'claim:one', kind: 'public_claim', label: 'Semantic claim', x: 100, y: 50},
    ], edges: [[0, 1], [0, 2], [1, 2]],
  }};
  const map = await mount({data, hash: '#o=universe%3Aall'});
  assert.equal(map.hotSegments().length, 1, 'root highlights the programme only');
  assert.equal(map.drawnSegments().length, 2, 'the ordinary problem-to-claim edge remains drawn');
  assert.equal(map.count.textContent, '3 shown');
  map.location.hash = '#o=claim%3Aone';
  map.window.fire('hashchange');
  assert.equal(map.hotSegments().length, 2, 'focusing the claim reveals both incident relationships');
  assert.equal(map.drawnSegments().length, 3);
  assert.equal(map.count.textContent, '3 shown');
});


test('friendly programme search normalizes only dashes and whitespace', async () => {
  const data = {initial: {nodes: [
    {id: 'problem:erdos_68', kind: 'problem', label: 'The factorial-denominator series',
      status: 'open', question: 'Factorial reciprocal irrationality remains open.', x: -100, y: 0},
    {id: 'claim:other', kind: 'public_claim', label: 'Erdos68.theorem', x: 100, y: 0},
  ], edges: [[0, 1]]}};
  const map = await mount({data});
  for (const query of ['Factorial denominator', 'The factorial-denominator series',
    ' FACTORIAL\t denominator ', 'factorial\u2011denominator', 'factorial\u2014denominator']) {
    map.search.value = query;
    map.search.fire('input');
    assert.match(map.count.textContent, /, 1 found$/, query);
    map.search.fire('keydown', {key: 'Enter'});
    assert.equal(map.location.hash, '#o=problem%3Aerdos_68');
    assert.match(map.inspector.innerHTML, /The factorial-denominator series/);
    assert.match(map.inspector.innerHTML, /Factorial reciprocal irrationality remains open/);
  }
  for (const query of ['Factorial denominater', 'Denominator factorial', 'erdos 68', 'Erdos68 theorem']) {
    map.search.value = query;
    map.search.fire('input');
    assert.match(map.count.textContent, /, none found$/, query);
    map.search.fire('keydown', {key: 'Enter'});
    assert.equal(map.location.hash, '#o=problem%3Aerdos_68', 'no-match Enter preserves the exact pin');
  }
  map.search.value = 'Erdos68.theorem';
  map.search.fire('input');
  assert.match(map.count.textContent, /, 1 found$/);
  map.search.fire('keydown', {key: 'Enter'});
  assert.equal(map.location.hash, '#o=claim%3Aother', 'qualified identifiers remain literal');
  map.search.value = '---';
  map.search.fire('input');
  map.search.fire('keydown', {key: 'Enter'});
  assert.equal(map.location.hash, '#o=claim%3Aother', 'punctuation alone creates no selectable matches');
});

test('normalized search preserves Enter kind order and reverse stepping', async () => {
  const data = {initial: {nodes: [
    {id: 'claim:factorial', kind: 'public_claim', label: 'A factorial-denominator criterion', x: 100, y: 0},
    {id: 'problem:erdos_68', kind: 'problem', label: 'The factorial-denominator series', x: -100, y: 0},
  ], edges: [[0, 1]]}};
  const map = await mount({data});
  map.search.value = 'Factorial denominator';
  map.search.fire('input');
  assert.match(map.count.textContent, /, 2 found$/);
  map.search.fire('keydown', {key: 'Enter'});
  assert.equal(map.location.hash, '#o=problem%3Aerdos_68');
  map.search.fire('keydown', {key: 'Enter'});
  assert.equal(map.location.hash, '#o=claim%3Afactorial');
  map.search.fire('keydown', {key: 'Enter', shiftKey: true});
  assert.equal(map.location.hash, '#o=problem%3Aerdos_68');
});


function restoredSearchFixture() {
  return {initial: {nodes: [
    {id: 'claim:factorial', kind: 'public_claim', label: 'A factorial-denominator criterion', x: 100, y: 0},
    {id: 'problem:erdos_68', kind: 'problem', label: 'The factorial-denominator series',
      status: 'open', question: 'Factorial reciprocal irrationality remains open.', x: -100, y: 0},
  ], edges: [[0, 1]]}};
}

test('cold history restoration reads the existing search value when data arrives', async () => {
  const map = await mount({data: restoredSearchFixture(), searchValue: 'Factorial denominator',
    hash: '#o=problem%3Aerdos_68'});
  assert.match(map.count.textContent, /, 2 found$/);
  assert.match(map.inspector.innerHTML, /Factorial reciprocal irrationality remains open/);
  map.search.fire('keydown', {key: 'Enter'});
  assert.equal(map.location.hash, '#o=claim%3Afactorial', 'restored pin advances in existing kind order');
  map.search.fire('keydown', {key: 'Enter', shiftKey: true});
  assert.equal(map.location.hash, '#o=problem%3Aerdos_68');
});

test('history lifecycle reconciles form values restored after the event task', async () => {
  const map = await mount({data: restoredSearchFixture(), queueTimers: true,
    hash: '#o=problem%3Aerdos_68'});
  map.zoom.fire('click');
  const before = map.span();
  map.window.fire('pageshow', {persisted: false});
  map.search.value = 'Factorial denominator'; // UA restoration after pageshow; no input event.
  map.flushTimers();
  assert.match(map.count.textContent, /, 2 found$/);
  assert.equal(map.location.hash, '#o=problem%3Aerdos_68', 'reconciliation does not repin');
  assert.equal(map.span(), before, 'reconciliation does not reset the camera');
  map.window.fire('popstate');
  map.search.value = 'criterion'; // Same-document traversal restores state after popstate.
  map.flushTimers();
  assert.match(map.count.textContent, /, 1 found$/);
  map.search.fire('keydown', {key: 'Enter'});
  assert.equal(map.location.hash, '#o=claim%3Afactorial');
});

test('BFcache pageshow preserves complete data, pin, lens and explored camera', async () => {
  const map = await fullHierarchy({queueTimers: true});
  map.claims.fire('click');
  map.search.value = 'Fan module';
  map.search.fire('input');
  map.search.fire('keydown', {key: 'Enter'});
  map.zoom.fire('click');
  const before = map.span();
  const hash = map.location.hash;
  const count = map.count.textContent;
  map.window.fire('pageshow', {persisted: true});
  map.flushTimers();
  assert.equal(map.count.textContent, count);
  assert.match(map.count.textContent, /, 96 found$/);
  assert.equal(map.location.hash, hash);
  assert.equal(map.claims.getAttribute('aria-pressed'), 'false');
  assert.equal(map.full.textContent, 'Complete universe loaded');
  assert.equal(map.requests.filter(url => url === 'graph').length, 1);
  assert.equal(map.span(), before);
  map.search.fire('keydown', {key: 'Enter'});
  assert.equal(map.location.hash, '#o=lean-module%3AFan01');
});

test('focus and Enter reconcile late restored values without creating false matches', async () => {
  const map = await mount({data: restoredSearchFixture(), hash: '#o=problem%3Aerdos_68'});
  map.search.value = 'Factorial denominator';
  map.search.fire('focus'); // Restored/autofilled DOM value need not emit input.
  assert.match(map.count.textContent, /, 2 found$/);
  map.search.value = 'criterion';
  map.search.fire('keydown', {key: 'Enter'}); // Also correct if focus preceded late restoration.
  assert.match(map.count.textContent, /, 1 found$/);
  assert.equal(map.location.hash, '#o=claim%3Afactorial');
  map.search.value = 'Factorial denominater';
  map.search.fire('keydown', {key: 'Enter'});
  assert.match(map.count.textContent, /, none found$/);
  assert.equal(map.location.hash, '#o=claim%3Afactorial', 'no-match Enter retains the pin');
  let stopped = false;
  map.search.fire('keydown', {key: 'Escape', stopPropagation() { stopped = true; }});
  assert.equal(stopped, true, 'search Escape stops the document pin-clear handler');
  assert.equal(map.search.value, '');
  assert.doesNotMatch(map.count.textContent, /found$/);
  assert.equal(map.location.hash, '#o=claim%3Afactorial', 'first Escape clears search only');
  stopped = false;
  map.search.fire('keydown', {key: 'Escape', stopPropagation() { stopped = true; }});
  if (!stopped) map.document.fire('keydown', {key: 'Escape', target: {tagName: 'INPUT'}});
  assert.equal(map.location.hash, '', 'second Escape bubbles to clear the pin');
});

/* The landing teaser: the same script drawn from the site root, which names
   maths/ in data-universe-base, beside a column of problem rows that the
   companion reads along with. */
async function mountTeaser({withCompanionHost = true} = {}) {
  let arcs = [];
  const context = new Proxy({
    clearRect() { arcs = []; },
    arc(x, y, r) { arcs.push({x, y, r}); },
    measureText(text) { return {width: String(text).length * 6}; },
  }, { get: (target, key) => target[key] ?? (() => {}) });
  const canvas = Object.assign(element({'data-universe-src': 'initial', 'data-universe-base': 'maths/'}), {
    clientWidth: 400, clientHeight: 400, getContext: () => context,
    getBoundingClientRect: () => ({left: 0, top: 0}),
  });
  const announced = [];
  const row = element({'data-problem-id': 'erdos_257'});
  const host = Object.assign(element(), {querySelector: s => s.startsWith('li.home-problem') ? row : null});
  const section = Object.assign(element(), {querySelector: s => s === '.home-split__text' ? host : null});
  const stage = Object.assign(element(), {
    querySelector: s => s === 'canvas' ? canvas : null,
    querySelectorAll: () => [],
    closest: s => s === 'section' && withCompanionHost ? section : null,
    dispatchEvent: event => { announced.push(event); return true; },
  });
  const appended = [];
  const document = Object.assign(element(), {
    readyState: 'complete', documentElement: element(), activeElement: null,
    head: {appendChild: node => { appended.push(node); }},
    createElement: () => element(),
    querySelector: () => null,
    querySelectorAll: s => s === '[data-universe-stage]' ? [stage] : [],
  });
  const location = {pathname: '/', search: '', hash: '', href: '/'};
  const window = Object.assign(element(), {
    location, devicePixelRatio: 1, isSecureContext: false,
    matchMedia: () => ({matches: true}),
    CustomEvent: class { constructor(type, init) { this.type = type; this.detail = init && init.detail; } },
  });
  const data = {initial: {
    nodes: [
      {id: 'problem:erdos_257', kind: 'problem', label: 'Reciprocal sums', x: -150, y: 0,
       sector: 'erdos_257', page: 'problems/erdos_257.html'},
      {id: 'statement:p257#thm:a', kind: 'paper_statement', label: 'Theorem 1.1', x: 150, y: 0,
       sector: 'erdos_257', paper: 'papers/p257.html#thm:a', lean_status: 'exact',
       comparator_status: 'compared', side: 'short'},
    ],
    edges: [[0, 1]],
    companion: {script: 'assets/universe-companion.js?v=1', style: 'assets/universe-companion.css?v=1',
                data: 'assets/universe-companion.json?v=1'},
    excerpts: [['p257', 'assets/excerpts/p257.json?v=1']],
  },
  // The teaser names excerpt routes relative to maths/, as the map does.
  'maths/assets/excerpts/p257.json?v=1': {schema: 'plectis_maths_universe_excerpts_v1', paper: 'p257',
    excerpts: [['statement:p257#thm:a', '', '<p><em>The paper’s own words.</em></p>']]},
  };
  vm.runInNewContext(source, {document, window, navigator: {}, CustomEvent: window.CustomEvent,
    getComputedStyle: () => ({getPropertyValue: () => ''}),
    fetch: async url => ({json: async () => data[url]}),
    setTimeout: fn => { fn(); return 1; }, clearTimeout() {},
  });
  await new Promise(resolve => setImmediate(resolve));
  // The statement is the rightmost disc drawn.
  const dot = arcs.reduce((best, a) => (best && best.x >= a.x ? best : a), null);
  return {canvas, location, announced, appended, dot};
}

// A teaser with Comparator and a frame clock the test drives, to follow the
// moment a settled hover plays.
async function mountPulse({reduceMotion = false, extraNodes = []} = {}) {
  let arcs = [];
  const context = new Proxy({
    clearRect() { arcs = []; },
    arc(x, y, r) { arcs.push({x, y, r, alpha: context.globalAlpha}); },
    measureText(text) { return {width: String(text).length * 6}; },
  }, { get: (target, key) => target[key] ?? (() => {}) });
  const canvas = Object.assign(element({'data-universe-src': 'initial', 'data-universe-base': 'maths/'}), {
    clientWidth: 400, clientHeight: 400, getContext: () => context,
    getBoundingClientRect: () => ({left: 0, top: 0}),
  });
  const stage = Object.assign(element(), {
    querySelector: s => s === 'canvas' ? canvas : null, querySelectorAll: () => [],
    closest: () => null, dispatchEvent: () => true,
  });
  const document = Object.assign(element(), {
    readyState: 'complete', documentElement: element(), activeElement: null,
    querySelector: () => null,
    querySelectorAll: s => s === '[data-universe-stage]' ? [stage] : [],
  });
  const frames = new Map();
  let nextFrame = 1, now = 0;
  const window = Object.assign(element(), {
    location: {pathname: '/', search: '', hash: '', href: '/'}, devicePixelRatio: 1, isSecureContext: false,
    matchMedia: query => ({matches: /reduce/.test(query) ? reduceMotion : true}),
    requestAnimationFrame: fn => { frames.set(nextFrame, fn); return nextFrame++; },
    cancelAnimationFrame: id => { frames.delete(id); },
  });
  const data = {initial: {
    nodes: [
      {id: 'integration:comparator', kind: 'integration_surface', label: 'Comparator', x: 0, y: -150},
      {id: 'problem:erdos_257', kind: 'problem', label: 'Reciprocal sums', x: -150, y: 0, sector: 'erdos_257'},
      {id: 'statement:p257#thm:a', kind: 'paper_statement', label: 'Theorem 1.1', x: 150, y: 0,
       sector: 'erdos_257', paper: 'papers/p257.html#thm:a', lean_status: 'exact',
       comparator_status: 'compared', side: 'short'},
      ...extraNodes,
    ],
    edges: [[0, 2], [1, 2]],
  }};
  vm.runInNewContext(source, {document, window, navigator: {},
    getComputedStyle: () => ({getPropertyValue: () => ''}),
    fetch: async url => ({json: async () => data[url]}),
    setTimeout: fn => { fn(); return 1; }, clearTimeout() {},
  });
  await new Promise(resolve => setImmediate(resolve));
  const comparator = arcs.reduce((best, a) => (best && best.y <= a.y ? best : a), null);
  const dot = arcs.reduce((best, a) => (best && best.x >= a.x ? best : a), null);
  // Run every frame due up to `ms` after the clock's start, sixteen at a time.
  const advanceTo = ms => {
    while (now < ms) {
      now += 16;
      const due = [...frames.entries()];
      frames.clear();
      for (const [, fn] of due) fn(now);
    }
  };
  return {canvas, comparator, dot, arcs: () => arcs, frames, advanceTo, now: () => now};
}

test('a settled hover sends one ripple and a bead of light along its thread to Comparator', async () => {
  const map = await mountPulse();
  const {dot, comparator} = map;
  map.canvas.fire('pointermove', {clientX: dot.x, clientY: dot.y});
  const start = map.now();
  const mid = {x: (dot.x + comparator.x) / 2, y: (dot.y + comparator.y) / 2};
  const near = (a, p, tolerance) => Math.hypot(a.x - p.x, a.y - p.y) <= tolerance;
  // Where a mark stands on the thread: its share of the way and its distance off it.
  const onThread = a => {
    const vx = comparator.x - dot.x, vy = comparator.y - dot.y, len2 = vx * vx + vy * vy;
    const u = ((a.x - dot.x) * vx + (a.y - dot.y) * vy) / len2;
    return {u, off: Math.abs((a.x - dot.x) * vy - (a.y - dot.y) * vx) / Math.sqrt(len2)};
  };
  map.advanceTo(start + 16 + 110 + 310);
  assert.ok(map.arcs().some(a => { const t = onThread(a); return a.r < dot.r + 2 && t.off < 1.5 && t.u > 0.3 && t.u < 0.7; }),
    'halfway through its travel a bead stands on the thread to Comparator, well clear of both ends');
  assert.ok(map.arcs().some(a => near(a, dot, 0.5) && a.r > dot.r + 8),
    'the hovered mark sends out a ripple wider than its hover ring');
  map.advanceTo(start + 2400);
  assert.ok(!map.arcs().some(a => near(a, mid, 6)), 'the bead is gone once the moment has played');
  assert.equal(map.frames.size, 0, 'and no frame keeps running after it');
});

test('under reduced motion a hover plays no ripple and sends no bead', async () => {
  const map = await mountPulse({reduceMotion: true});
  const {dot, comparator} = map;
  map.canvas.fire('pointermove', {clientX: dot.x, clientY: dot.y});
  map.advanceTo(map.now() + 16 + 110 + 310);
  const mid = {x: (dot.x + comparator.x) / 2, y: (dot.y + comparator.y) / 2};
  assert.ok(!map.arcs().some(a => Math.hypot(a.x - mid.x, a.y - mid.y) <= 6), 'no bead travels');
  assert.ok(!map.arcs().some(a => Math.hypot(a.x - dot.x, a.y - dot.y) <= 0.5 && a.r > dot.r + 8), 'no ripple');
  assert.equal(map.frames.size, 0, 'nothing is scheduled');
});

test('without the column a teaser dot opens the full map on it, under the base the landing names', async () => {
  const teaser = await mountTeaser({withCompanionHost: false});
  teaser.canvas.fire('click', {clientX: teaser.dot.x, clientY: teaser.dot.y});
  assert.equal(teaser.location.href, 'maths/universe.html#o=statement%3Ap257%23thm%3Aa',
    'a click selects the result where its card offers the ways out (a root-relative route 404ed)');
});

test('beside the column a click pins the result instead of leaving the page', async () => {
  const teaser = await mountTeaser();
  const selects = () => teaser.announced.filter(event => event.type === 'universe:select');
  teaser.canvas.fire('pointermove', {clientX: teaser.dot.x, clientY: teaser.dot.y});
  teaser.canvas.fire('click', {clientX: teaser.dot.x, clientY: teaser.dot.y});
  assert.equal(teaser.location.href, '/', 'the page stays where it is');
  const pinned = selects().pop();
  assert.ok(pinned && pinned.detail, 'the click pins the result for the column');
  assert.equal(pinned.detail.id, 'statement:p257#thm:a');
  assert.equal(pinned.detail.href, 'maths/papers/p257.html#thm:a', 'the card can still go to the paper');
  teaser.canvas.fire('click', {clientX: teaser.dot.x, clientY: teaser.dot.y});
  assert.equal(selects().pop().detail, null, 'a click on the pinned dot lets it go');
  assert.equal(teaser.location.href, '/', 'and still leaves the page where it is');
});

test('beside a problem column the teaser announces what it hovers and loads the companion', async () => {
  const teaser = await mountTeaser();
  assert.deepEqual(teaser.appended.map(node => node.href || node.src), [
    'maths/assets/universe-companion.css?v=1', 'maths/assets/universe-companion.js?v=1'],
    'the companion style and script load from maths/');
  teaser.canvas.fire('pointermove', {clientX: teaser.dot.x, clientY: teaser.dot.y});
  const hover = teaser.announced.filter(event => event.type === 'universe:hover').pop();
  assert.ok(hover && hover.detail, 'hovering a dot announces it');
  assert.equal(hover.detail.sector, 'erdos_257');
  assert.equal(hover.detail.tier, 'replayed');
  assert.equal(hover.detail.href, 'maths/papers/p257.html#thm:a');
  assert.equal(hover.detail.mapHref, 'maths/universe.html#o=statement%3Ap257%23thm%3Aa');
  teaser.canvas.fire('pointerleave');
  assert.equal(teaser.announced.filter(event => event.type === 'universe:hover').pop().detail, null,
    'leaving the drawing announces nothing under the pointer');
});

// A paper result, its neighbour in the same paper and a claim on the same
// Lean theorem, with the excerpt file and the statement detail the card reads.
function resultCardData() {
  return {
    initial: {
      nodes: [
        {id: 'problem:erdos_257', kind: 'problem', label: 'Reciprocal sums', short: '#257', x: -200, y: 0, sector: 'erdos_257'},
        {id: 'statement:p257#thm:a', kind: 'paper_statement', label: 'Theorem 1.1 (Half membership)', x: 150, y: 0,
         sector: 'erdos_257', paper: 'papers/p257.html#thm:a', lean_status: 'exact_or_stronger',
         comparator_status: 'compared', palomar_status: 'prepared', side: 'short', line: 40,
         decls: [['Erdos257.half_mem', 0, 12], ['Erdos257.half_mem_iff', 0, 30]], cmp_entries: [0], cmp_runs: [0]},
        {id: 'statement:p257#thm:b', kind: 'paper_statement', label: 'Theorem 1.2 (Cap)', x: 150, y: 90,
         sector: 'erdos_257', paper: 'papers/p257.html#thm:b', lean_status: 'exact', comparator_status: 'pending',
         palomar_status: 'pending', side: 'short', line: 60},
        {id: 'claim:half', kind: 'public_claim', label: 'Half membership claim', x: 0, y: 160, status: 'proved here'},
      ],
      edges: [[0, 1, 0], [3, 1, 1]],
      relations: ['states', 'same_lean_declaration'],
      statements: {summary: {replay_run: '359', replay_href: 'https://example.test/run/359'},
        lean_files: ['Erdos257/Half.lean'], comparator_entries: ['E257_1'], comparator_runs: ['359'],
        lean_source_base: 'https://example.test/blob/pin/', tex_source_base: 'https://example.test/blob/main/',
        tex_paths: {p257: 'papers/p257.tex'}},
      excerpts: [['p257', 'assets/excerpts/p257.json?v=1']],
    },
    'assets/excerpts/p257.json?v=1': {schema: 'plectis_maths_universe_excerpts_v1', paper: 'p257', excerpts: [
      ['statement:p257#thm:a', 'Half <math><mi>A</mi></math> membership',
       '<p><em>Suppose <span class="math inline"><math><mi>n</mi></math></span>. Then see Theorem ' +
       '<a class="math-ref" href="papers/p257.html#thm:b" data-universe-ref="statement:p257#thm:b">1.2</a>.</em></p>'],
      ['statement:p257#thm:b', '', '<p><em>The cap holds.</em></p>'],
    ]},
    detail: {replay: {run_id: '359', href: 'https://example.test/run/359'}, statements: {'statement:p257#thm:a': {
      statements: {'Erdos257.half_mem': 'theorem half_mem : (1 / 2 : ℝ) ∈ A'},
      relation_note: 'Items one and two give it.', html_mathml: {relation_note: 'Items one and two give it.'},
      record: 'https://example.test/record', named_inputs: [],
      checks: [{declaration: 'Erdos257.half_mem', entry: 'E257_1', same_as_lean: true,
                challenge: 'https://example.test/c', solution: 'https://example.test/s', receipt: 'https://example.test/r'}]}}},
  };
}

test('a result card quotes its paper first, then says in words how it is checked, code one step down', async () => {
  const map = await mount({data: resultCardData(), attrs: {'data-universe-detail': 'detail'},
    hash: '#o=statement%3Ap257%23thm%3Aa'});
  await map.settle();
  await map.settle();
  const html = map.inspector.innerHTML;
  assert.match(html, /<h2 class="universe-inspector__title">Half <math><mi>A<\/mi><\/math> membership<\/h2>/,
    'the title is the printed name, its maths typeset');
  assert.match(html, /<b>Theorem 1\.1<\/b> in the short paper/);
  assert.match(html, /<blockquote class="universe-quote__text"><p><em>Suppose/, 'the paper’s own words come first');
  assert.ok(html.indexOf('universe-quote__text') < html.indexOf('How it is checked'));
  assert.match(html, /class="universe-go universe-go--primary universe-open--primary" href="papers\/p257\.html#thm:a">Read it in the paper/,
    'the paper button keeps the hook the site’s navigation warming reads');
  for (const station of ['Lean', 'Comparator', 'Palomar']) assert.match(html, new RegExp(`<b>${station}\\.</b>`));
  assert.match(html, /It states this result or something stronger, in 2 theorems\./);
  assert.match(html, /In <a[^>]*>run 359<\/a> its corpus entry E257_1 passed, the Lean kernel and nanoda both accepting it\./,
    'acceptance is the corpus entry’s, as its receipt is');
  assert.match(html, /Nothing has been submitted\./, 'Palomar holds a prepared corpus only');
  assert.match(html, /How the Lean statement gives the printed one: Items one and two give it\./);
  const code = html.indexOf('<pre');
  assert.ok(code > html.indexOf('<details class="universe-lean"'), 'Lean code sits inside the disclosure, never on the card face');
  assert.match(html, /On the same Lean theorems[\s\S]*Half membership claim/);
  // A reference in the quote to another result on the map selects it there.
  map.inspector.fire('click', {target: {closest: s => s === '[data-universe-ref]'
    ? {getAttribute: () => 'statement:p257#thm:b'} : null}});
  await map.settle();
  assert.match(map.inspector.innerHTML, /<h2 class="universe-inspector__title">Cap<\/h2>/);
  assert.match(map.inspector.innerHTML, /The cap holds\./);
  assert.match(map.inspector.innerHTML, /Its replay is queued\./);
  assert.equal(map.location.hash, '#o=statement%3Ap257%23thm%3Ab');
});

test('a double-click on a result opens it at its place in its paper', async () => {
  const map = await mount({data: resultCardData()});
  const arcs = map.arcs();
  const right = Math.max(...arcs.map(a => a.x));
  const dot = arcs.filter(a => Math.abs(a.x - right) < 0.5).reduce((best, a) => (best && best.y <= a.y ? best : a), null);
  map.canvas.fire('click', {clientX: dot.x, clientY: dot.y, detail: 1});
  assert.equal(map.location.href, undefined, 'the first click only selects');
  map.canvas.fire('click', {clientX: dot.x, clientY: dot.y, detail: 2});
  assert.equal(map.location.href, 'papers/p257.html#thm:a');
  const teaser = await mountTeaser();
  teaser.canvas.fire('click', {clientX: teaser.dot.x, clientY: teaser.dot.y, detail: 1});
  assert.equal(teaser.location.href, '/', 'beside the column the first click pins');
  teaser.canvas.fire('click', {clientX: teaser.dot.x, clientY: teaser.dot.y, detail: 2});
  assert.equal(teaser.location.href, 'maths/papers/p257.html#thm:a', 'the second goes to the paper, not back to nothing');
});

test('over the map the wheel zooms; a scroll already moving the page carries on past it', async () => {
  const map = await mount();
  let prevented = 0;
  const wheel = (deltaY, timeStamp) => map.canvas.fire('wheel', {deltaY, deltaMode: 0, clientX: 146, clientY: 170,
    timeStamp, preventDefault() { prevented++; }});
  const before = map.span();
  wheel(-120, 5000);
  assert.ok(map.span() > before, 'a plain wheel over the map zooms in, no key held');
  assert.equal(prevented, 1, 'and the page does not scroll under it');
  const zoomed = map.span();
  map.window.fire('wheel', {target: {}, timeStamp: 9000});
  wheel(120, 9100);
  assert.equal(map.span(), zoomed, 'a page scroll that slides the map under the pointer keeps scrolling the page');
  assert.equal(prevented, 1);
  wheel(120, 9800);
  assert.ok(map.span() < zoomed, 'once the page has come to rest the wheel zooms again');
});

test('motion (2026-10-04): teasers open once in view, reduced motion is live, DPR is capped', () => {
  // A teaser waits closed and plays the map's opening once, when the canvas
  // is first well in view; a reveal that cannot animate opens at once.
  assert.match(source, /var teaserOpening = !pageMode && !reduceMotion/);
  assert.match(source, /new IntersectionObserver\(function \(entries\) \{[\s\S]{0,200}?seen\.disconnect\(\);\s*startReveal\(\);/);
  assert.match(source, /function startReveal\(\) \{\s*if \(reduceMotion \|\| !window\.requestAnimationFrame \|\| document\.hidden\) \{\s*if \(reveal < 1\) \{ reveal = 1; draw\(\); \}/);
  // Turning reduced motion on part-way stops the motion and draws the still map.
  assert.match(source, /function followReduceMotion\(\) \{\s*reduceMotion = !!\(reduceQuery && reduceQuery\.matches\);/);
  // The backing store is capped at twice the CSS size, as the plait's is.
  assert.match(source, /var dpr = Math\.min\(window\.devicePixelRatio \|\| 1, 2\);/);
  assert.doesNotMatch(source, /var dpr = window\.devicePixelRatio \|\| 1;/);
});

test('beside the column a hovered result reaches the card with its paper’s words, sent again once they arrive', async () => {
  const teaser = await mountTeaser();
  const hovers = () => teaser.announced.filter(event => event.type === 'universe:hover' && event.detail);
  teaser.canvas.fire('pointermove', {clientX: teaser.dot.x, clientY: teaser.dot.y});
  assert.equal(hovers()[0].detail.quote, null, 'the hover goes out at once, before the excerpt file is in');
  await new Promise(resolve => setImmediate(resolve));
  const last = hovers().pop();
  assert.equal(last.detail.id, 'statement:p257#thm:a');
  assert.equal(last.detail.quote, '<p><em>The paper’s own words.</em></p>',
    'the same result is sent again with the words the card quotes');
  assert.ok(!('decls' in last.detail), 'the card no longer carries a declaration name to print');
});

test('a gap between two dots under a sweeping pointer keeps the field dimmed, then lets it go', async () => {
  // A paper with no thread to the result: the field dims it while the result is in focus.
  const map = await mountPulse({extraNodes: [{id: 'paper:far', kind: 'paper', label: 'Far paper', x: -150, y: 150}]});
  const far = () => map.arcs().filter(a => a.x < map.dot.x && a.y > map.dot.y + 20)
    .reduce((best, a) => (best && best.r >= a.r ? best : a), null);
  const rest = far().alpha;
  map.canvas.fire('pointermove', {clientX: map.dot.x, clientY: map.dot.y});
  map.advanceTo(map.now() + 400);
  const dim = far().alpha;
  assert.ok(dim < rest - 0.2, 'a result in focus dims the unconnected paper');
  map.canvas.fire('pointermove', {clientX: 2, clientY: 2});
  map.advanceTo(map.now() + 48);
  assert.ok(far().alpha < rest - 0.2, 'the gap after a dot holds the dim instead of snapping the field bright');
  map.canvas.fire('pointermove', {clientX: map.dot.x, clientY: map.dot.y});
  map.advanceTo(map.now() + 32);
  assert.ok(far().alpha <= dim + 0.02, 'the next dot carries on from the held dim, never restarting from nothing');
  map.canvas.fire('pointermove', {clientX: 2, clientY: 2});
  map.advanceTo(map.now() + 900);
  assert.ok(Math.abs(far().alpha - rest) < 0.02, 'once the pointer has really left, the field eases back');
  assert.equal(map.frames.size, 0, 'and nothing keeps running');
});

test('under the map a tap on a dot brings its card into view; beside the map nothing scrolls', async () => {
  const smallest = arcs => arcs.reduce((best, a) => (best && best.r <= a.r ? best : a), null);
  const phone = await mount({inspectorTop: 900});
  const claim = smallest(phone.arcs());
  phone.canvas.fire('click', {clientX: claim.x, clientY: claim.y, detail: 1});
  assert.match(phone.inspector.innerHTML, /One checked claim/, 'the tap pins the claim');
  assert.equal(phone.scrolled.length, 1, 'the card under the map scrolls into view');
  assert.equal(phone.scrolled[0].block, 'start');
  const desk = await mount({inspectorTop: 0});
  const dot = smallest(desk.arcs());
  desk.canvas.fire('click', {clientX: dot.x, clientY: dot.y, detail: 1});
  assert.equal(desk.scrolled.length, 0, 'a card beside the map stays where it is');
});

/* The structure pass (4 October 2026): the results ring carries a scale with
   a tick for every result, the pinned result has a cursor on it, a focus is
   framed by a reticle and named on a plate at the end of a leader, the
   opening assembles the rings once, and nothing paints out of view. This
   harness adds bands, a controllable IntersectionObserver, a frame clock
   and a canvas that records what each paint draws. */
function structureData() {
  const at = (r, angle) => ({x: r * Math.cos(angle), y: r * Math.sin(angle)});
  const result = (paper, n, sector, angle, r, side) => ({
    id: `statement:${paper}#r${n}`, kind: 'paper_statement', label: `Theorem ${n}.1 (Result ${n} of ${paper})`,
    sector, side, line: n * 10, lean_status: 'exact', comparator_status: 'compared',
    paper: `papers/${paper}.html#r${n}`, ...at(r, angle)});
  const nodes = [
    {id: 'universe:all', kind: 'universe', label: 'Lean universe', short: 'Lean universe', x: 0, y: 0},
    {id: 'problem:p1', kind: 'problem', label: 'First problem', short: '#1', sector: 'p1', ...at(250, -1.57)},
    {id: 'problem:p2', kind: 'problem', label: 'Second problem', short: '#2', sector: 'p2', ...at(250, 1.57)},
    {id: 'problem:p3', kind: 'problem', label: 'Third problem', short: '#3', sector: 'p3', ...at(250, 0)},
    // The first problem's long record, on the orbit beside it.
    {id: 'paper:a-long', kind: 'paper', label: 'The first long record', short: 'The first long record', sector: 'p1', ...at(250, -1.95)},
    // The first sector: a short paper of two results and a long record of four.
    result('a-short', 1, 'p1', -2.2, 350, 'short'), result('a-short', 2, 'p1', -2.0, 350, 'short'),
    result('a-long', 1, 'p1', -2.2, 364, 'long'), result('a-long', 2, 'p1', -1.8, 364, 'long'),
    result('a-long', 3, 'p1', -1.4, 364, 'long'), result('a-long', 4, 'p1', -1.0, 364, 'long'),
    // The second: a long record of four.
    result('b-long', 1, 'p2', 1.0, 364, 'long'), result('b-long', 2, 'p2', 1.4, 364, 'long'),
    result('b-long', 3, 'p2', 1.8, 364, 'long'), result('b-long', 4, 'p2', 2.2, 364, 'long'),
    // The third, at the right-hand edge, beside its own problem.
    result('c-long', 1, 'p3', 0, 380, 'long'),
  ];
  const bands = [
    {sector: 'p1', lo: -2.4, hi: -0.74, rings: {short: [350, 350, 2], long: [364, 373, 4]}, title: '#1 First problem', evidence: {replayed: 6}},
    {sector: 'p2', lo: 0.74, hi: 2.4, rings: {long: [364, 373, 4]}, title: '#2 Second problem', evidence: {replayed: 4}},
    {sector: 'p3', lo: -0.3, hi: 0.3, rings: {long: [380, 380, 1]}, title: '#3 Third problem', evidence: {replayed: 1}},
  ];
  return {initial: {nodes, edges: [[0, 1], [0, 2], [0, 3]], bands,
    companion: {script: 'assets/universe-companion.js?v=1', style: 'assets/universe-companion.css?v=1',
                data: 'assets/universe-companion.json?v=1'}}};
}

async function mountStructure({page = false, reduceMotion = false, csp = null, companion = false, speculation = false,
  withInspector = false, data = structureData} = {}) {
  let arcs = [], strokes = [], fills = [], rects = [], labels = [], path = [], pen = null, paints = 0, dash = [], images = 0;
  const context = new Proxy({
    clearRect() { arcs = []; strokes = []; fills = []; rects = []; labels = []; images = 0; paints++; },
    beginPath() { path = []; pen = null; },
    moveTo(x, y) { pen = [x, y]; },
    lineTo(x, y) { if (pen) path.push({from: pen, to: [x, y]}); pen = [x, y]; },
    setLineDash(segments) { dash = segments; },
    stroke() { strokes.push({style: context.strokeStyle, alpha: context.globalAlpha, width: context.lineWidth, dashed: dash.length > 0, segments: path.slice()}); },
    fill() { fills.push({style: context.fillStyle, alpha: context.globalAlpha}); },
    fillRect(x, y, w, h) { rects.push({x, y, w, h, alpha: context.globalAlpha}); },
    arc(x, y, r, a0, a1) { arcs.push({x, y, r, a0, a1, alpha: context.globalAlpha}); },
    drawImage() { images++; },
    measureText(text) { return {width: String(text).length * 6}; },
    fillText(text, x, y) { labels.push({text, x, y, alpha: context.globalAlpha}); },
  }, { get: (target, key) => target[key] ?? (() => {}) });
  const canvas = Object.assign(element({'data-universe-src': 'initial', 'data-universe-base': 'maths/'}), {
    clientWidth: 640, clientHeight: 600, getContext: () => context,
    getBoundingClientRect: () => ({left: 0, top: 0, bottom: 600}),
  });
  if (page) canvas.classList.add('universe-canvas--page');
  const announced = [];
  const row = element({'data-problem-id': 'p1'});
  const host = Object.assign(element(), {querySelector: s => s.startsWith('li.home-problem') ? row : null});
  const section = Object.assign(element(), {querySelector: s => s === '.home-split__text' ? host : null});
  const caption = element();
  const stage = Object.assign(element(), {
    querySelector: s => s === 'canvas' ? canvas : s === '.universe-caption' ? caption : null, querySelectorAll: () => [],
    closest: s => s === 'section' && companion ? section : null,
    dispatchEvent: event => { announced.push(event); return true; },
  });
  const appended = [];
  const meta = csp ? Object.assign(element({content: csp})) : null;
  const inspector = withInspector ? element() : null;
  const document = Object.assign(element(), {
    readyState: 'complete', documentElement: element(), activeElement: null,
    head: {appendChild: node => { appended.push(node); }},
    createElement: () => element(),
    querySelector: s => (s.indexOf('Content-Security-Policy') !== -1 ? meta : s === '[data-universe-inspector]' ? inspector : null),
    querySelectorAll: s => s === '[data-universe-stage]' ? [stage] : [],
  });
  const observers = [];
  class IO {
    constructor(callback, options) { this.callback = callback; this.options = options; observers.push(this); }
    observe(target) { this.target = target; }
    disconnect() { this.gone = true; }
  }
  const frames = new Map();
  let nextFrame = 1, now = 0, rafCalls = 0;
  const location = {pathname: page ? '/maths/universe.html' : '/', search: '', hash: '', href: 'https://example.test/'};
  const CustomEvent = class { constructor(type, init) { this.type = type; this.detail = init && init.detail; } };
  const window = Object.assign(element(), {
    location, devicePixelRatio: 1, isSecureContext: false,
    history: {replaceState(_a, _b, url) { location.hash = new URL(url, 'http://test').hash; }},
    matchMedia: query => ({matches: /reduce/.test(query) ? reduceMotion : true}),
    requestAnimationFrame: fn => { rafCalls++; frames.set(nextFrame, fn); return nextFrame++; },
    cancelAnimationFrame: id => { frames.delete(id); },
    IntersectionObserver: IO, CustomEvent,
  });
  const sandbox = {document, window, navigator: {}, CustomEvent, IntersectionObserver: IO, URL,
    getComputedStyle: () => ({getPropertyValue: () => ''}),
    fetch: async url => ({json: async () => data()[url]}),
    setTimeout: fn => { fn(); return 1; }, clearTimeout() {}};
  if (speculation) sandbox.HTMLScriptElement = {supports: type => type === 'speculationrules'};
  vm.runInNewContext(source, sandbox);
  await new Promise(resolve => setImmediate(resolve));
  const advanceTo = ms => {
    while (now < ms) {
      now += 16;
      const due = [...frames.entries()];
      frames.clear();
      for (const [, fn] of due) fn(now);
    }
  };
  // The field's centre: every ring and plate is an arc about it.
  const centre = () => {
    const tally = new Map();
    for (const a of arcs) {
      const key = `${a.x.toFixed(2)},${a.y.toFixed(2)}`;
      tally.set(key, (tally.get(key) || 0) + 1);
    }
    const [key] = [...tally.entries()].sort((p, q) => q[1] - p[1])[0];
    const [x, y] = key.split(',').map(Number);
    return {x, y};
  };
  // Screen place of a node, from where its problem is drawn.
  const scale = () => {
    const c = centre();
    const p = arcs.filter(a => a.r >= 13).map(a => Math.hypot(a.x - c.x, a.y - c.y)).filter(d => d > 100 && d < 200);
    return p.length ? p[0] / 250 : 1;
  };
  const place = id => {
    const n = structureData().initial.nodes.find(m => m.id === id);
    const c = centre(), k = scale();
    return {x: c.x + n.x * k, y: c.y + n.y * k};
  };
  // The camera in any view: the orbit through the problems (radius 250 in
  // the fixture) is the widest whole circle drawn about the centre.
  const view = () => {
    const c = centre();
    const whole = arcs.filter(a => Math.hypot(a.x - c.x, a.y - c.y) < 0.01 && Math.abs((a.a1 - a.a0) - 2 * Math.PI) < 1e-9);
    return {k: Math.max(...whole.map(a => a.r)) / 250, tx: c.x, ty: c.y};
  };
  const at = id => {
    const n = data().initial.nodes.find(m => m.id === id), v = view();
    return {x: v.tx + n.x * v.k, y: v.ty + n.y * v.k};
  };
  const results = () => {
    const c = centre();
    return arcs.filter(a => a.r < 4 && Math.hypot(a.x - c.x, a.y - c.y) > 190);
  };
  // The cursor: one ink bar twelve pixels long across the scale.
  const cursor = () => {
    const c = centre();
    const bar = strokes.find(s => s.style === '#211318' && s.width === 2 && s.segments.length === 1 &&
      Math.abs(Math.hypot(s.segments[0].to[0] - s.segments[0].from[0], s.segments[0].to[1] - s.segments[0].from[1]) - 12) < 0.01);
    return bar ? Math.atan2(bar.segments[0].from[1] - c.y, bar.segments[0].from[0] - c.x) : null;
  };
  // The scale's ticks: short radial strokes standing out past the deepest plate.
  const ticks = () => {
    const c = centre();
    return strokes.filter(s => s.style === '#211318' && s.width === 1).flatMap(s => s.segments)
      .filter(seg => Math.hypot(seg.from[0] - c.x, seg.from[1] - c.y) > 200);
  };
  return {canvas, caption, document, window, location, announced, appended, frames, advanceTo, now: () => now,
    rafCalls: () => rafCalls, paints: () => paints, arcs: () => arcs, rects: () => rects, labels: () => labels,
    strokes: () => strokes, images: () => images, inspector, centre, place, view, at, results, cursor, ticks,
    intersect(on) { for (const o of observers) if (!o.gone) o.callback([{isIntersecting: on, target: o.target}]); },
    atlas(view, previous) { document.fire('plectis:atlas', {detail: {view, previous, phase: 'start', instant: false}}); },
    key(key) { document.fire('keydown', {key, target: {tagName: 'BODY'}}); },
  };
}

test('the teaser assembles once, ring by ring, and a trip away on the atlas and back replays nothing', async () => {
  const map = await mountStructure();
  assert.equal(map.frames.size, 0, 'closed and still until it comes into view');
  assert.ok(map.results().every(a => a.alpha < 0.01), 'no result shows before the teaser is in view');
  map.intersect(true);
  assert.ok(map.frames.size > 0, 'coming into view starts the opening');
  const start = map.now();
  map.advanceTo(start + 16 + 200);
  const core = map.arcs().filter(a => a.r > 10 && Math.hypot(a.x - map.centre().x, a.y - map.centre().y) < 0.5);
  assert.ok(core.some(a => a.alpha > 0.5), 'the core is up first');
  assert.ok(map.results().every(a => a.alpha < 0.01), 'while the results ring has not begun');
  map.advanceTo(start + 16 + 352);
  const seating = map.results().map(a => Math.hypot(a.x - map.centre().x, a.y - map.centre().y));
  assert.ok(map.results().some(a => a.alpha > 0.1 && a.alpha < 0.9), 'the results ring is arriving');
  map.advanceTo(start + 2000);
  assert.equal(map.frames.size, 0, 'the opening ends and nothing keeps running');
  const final = map.results().map(a => Math.hypot(a.x - map.centre().x, a.y - map.centre().y));
  assert.ok(seating.every((d, i) => d < final[i] - 1), 'arriving, the ring stood inside its place and seated outward');
  assert.ok(map.results().every(a => a.alpha > 0.99), 'every result is drawn whole');
  assert.ok(map.ticks().length >= 10, 'the scale has a tick for every result');
  const paints = map.paints();
  map.atlas('system', 'mathematics');
  map.intersect(false);
  map.advanceTo(map.now() + 600);
  map.intersect(true);
  map.atlas('mathematics', 'system');
  map.advanceTo(map.now() + 600);
  assert.equal(map.frames.size, 0, 'coming back plays nothing');
  assert.ok(map.paints() <= paints + 2, 'and costs no more than a repaint');
  assert.ok(map.results().every(a => a.alpha > 0.99), 'the field is simply there, whole');
});

test('an opening cut short by the atlas is spent at once, and nothing paints while away', async () => {
  const map = await mountStructure();
  map.intersect(true);
  map.advanceTo(map.now() + 16 + 150);
  map.intersect(false);
  assert.equal(map.frames.size, 0, 'leaving view stops the opening there and then');
  const paints = map.paints();
  map.document.fire('plectis:theme');
  map.window.fire('resize');
  assert.equal(map.paints(), paints, 'a theme change or a resize waits while the canvas is away');
  map.intersect(true);
  assert.equal(map.paints(), paints + 1, 'and is painted once when it is back');
  assert.equal(map.frames.size, 0, 'with no opening replayed');
  assert.ok(map.results().every(a => a.alpha > 0.99), 'the opening that was cut short is spent, not resumed');
});

test('once the field has settled no animation frame is asked for at rest', async () => {
  const map = await mountStructure();
  map.intersect(true);
  map.advanceTo(map.now() + 2000);
  assert.equal(map.frames.size, 0);
  const calls = map.rafCalls();
  map.advanceTo(map.now() + 3000);
  map.document.fire('plectis:theme');
  map.window.fire('resize');
  assert.equal(map.rafCalls(), calls, 'a theme change or a resize repaints in place without a frame loop');
});

test('the cursor marks the pinned result’s place in its paper and moves only when the pin does', async () => {
  const map = await mountStructure({page: true});
  map.advanceTo(map.now() + 2000);
  assert.equal(map.frames.size, 0, 'the map’s own opening has played and stopped');
  assert.equal(map.cursor(), null, 'no cursor without a pin');
  // Every tick stands at one spacing, the closest any sector packs its
  // results less a twentieth, and each sector's run is centred in it.
  const step = Math.min((-0.74 + 2.4) / 6, (2.4 - 0.74) / 4, 0.6 / 1) * 0.95;
  const lo = (-2.4 - 0.74) / 2 - 3 * step;
  // The long record's first result is the third tick of six: the short
  // paper's two come first.
  const a = map.place('statement:a-long#r1'), b = map.place('statement:a-long#r3');
  map.canvas.fire('click', {clientX: a.x, clientY: a.y, detail: 1});
  map.advanceTo(map.now() + 400);
  assert.ok(Math.abs(map.cursor() - (lo + 2.5 * step)) < 1e-3, 'the pin sets the cursor on its own tick, without travel');
  map.advanceTo(map.now() + 2000);
  assert.equal(map.frames.size, 0, 'and everything rests');
  const pinnedAt = map.cursor();
  map.canvas.fire('pointermove', {clientX: b.x, clientY: b.y});
  map.advanceTo(map.now() + 2000);
  assert.ok(Math.abs(map.cursor() - pinnedAt) < 1e-9, 'a hover elsewhere leaves it where it is');
  map.canvas.fire('pointermove', {clientX: 2, clientY: 2});
  map.advanceTo(map.now() + 2000);
  assert.ok(Math.abs(map.cursor() - pinnedAt) < 1e-9, 'idle, it never moves by itself');
  map.canvas.fire('click', {clientX: b.x, clientY: b.y, detail: 1});
  map.advanceTo(map.now() + 112);
  const between = map.cursor(), target = lo + 4.5 * step;
  assert.ok(between > pinnedAt + 0.01 && between < target - 0.01, 'a new pin turns it along the scale');
  map.advanceTo(map.now() + 2000);
  assert.ok(Math.abs(map.cursor() - target) < 1e-3, 'to the new result’s tick');
  assert.equal(map.frames.size, 0, 'where it stops');
});

test('under reduced motion the field, its scale and the cursor are drawn final at once', async () => {
  const teaser = await mountStructure({reduceMotion: true});
  teaser.intersect(true);
  assert.equal(teaser.frames.size, 0, 'no opening plays');
  assert.ok(teaser.results().length && teaser.results().every(a => a.alpha > 0.99), 'every result is drawn whole');
  assert.ok(teaser.ticks().length >= 10, 'with its scale');
  const map = await mountStructure({page: true, reduceMotion: true});
  assert.equal(map.frames.size, 0, 'the map page opens still too');
  const a = map.place('statement:a-long#r1');
  map.canvas.fire('click', {clientX: a.x, clientY: a.y, detail: 1});
  assert.ok(map.cursor() !== null, 'a pin shows its cursor at once');
  assert.equal(map.frames.size, 0, 'and asks for no frame');
});

test('a reticle frames the focus and its name plate keeps clear of a problem’s disc', async () => {
  const map = await mountStructure({page: true});
  map.advanceTo(map.now() + 2000);
  // The third sector's one result sits at the right-hand edge with its own
  // problem just inward of it: beside it to the left, a plate would lie
  // across the problem.
  const dot = map.place('statement:c-long#r1'), problem = map.place('problem:p3');
  map.canvas.fire('pointermove', {clientX: dot.x, clientY: dot.y});
  map.advanceTo(map.now() + 2000);
  const name = map.labels().find(l => l.text.startsWith('Theorem 1.1 ('));
  assert.ok(name, 'the hovered result names itself on a plate');
  const half = name.text.length * 3 + 9;
  const plate = {x0: name.x - half, x1: name.x + half, y0: name.y - 16, y1: name.y + 7};
  const disc = {x0: problem.x - 14, x1: problem.x + 14, y0: problem.y - 14, y1: problem.y + 14};
  const overlaps = plate.x0 < disc.x1 && plate.x1 > disc.x0 && plate.y0 < disc.y1 && plate.y1 > disc.y0;
  assert.ok(!overlaps, 'the plate is set where it covers no problem');
  // Four corners of hairline about the mark: each a level and an upright run.
  const near = map.rects().filter(r => Math.abs(r.x + r.w / 2 - dot.x) < 20 && Math.abs(r.y + r.h / 2 - dot.y) < 20);
  assert.ok(near.length >= 8, 'four corner ticks frame the mark');
  assert.ok(near.every(r => r.w <= 1 + 1e-9 || r.h <= 1 + 1e-9), 'each a single device pixel wide');
});

test('going back retraces the drill: result, paper, problem, whole field, each with its card and frame', async () => {
  const map = await mountStructure({page: true, withInspector: true});
  map.advanceTo(map.now() + 2000);
  const fitted = map.view().k;
  const click = id => { const p = map.at(id); map.canvas.fire('click', {clientX: p.x, clientY: p.y, detail: 1}); map.advanceTo(map.now() + 2000); };
  const hint = () => (map.inspector.innerHTML.match(/click empty ground to ([^.<]*)/) || [])[1];
  // Down: the problem frames its sector, a paper of it frames its results,
  // and a result of that paper pins its card where it is.
  click('problem:p1');
  assert.equal(map.location.hash, '#o=problem%3Ap1');
  const sector = map.view().k;
  assert.ok(sector > fitted * 1.3, 'the problem frames its sector, closer in');
  assert.equal(hint(), 'go back to the whole map');
  assert.match(map.inspector.innerHTML, />Close<\/button>/, 'at the top of the trail the card closes');
  click('paper:a-long');
  assert.equal(map.location.hash, '#o=paper%3Aa-long');
  const paperView = map.view();
  assert.equal(hint(), 'go back to #1', 'the card names the level above');
  click('statement:a-long#r2');
  assert.equal(map.location.hash, '#o=statement%3Aa-long%23r2');
  assert.ok(Math.abs(map.view().k - paperView.k) < 1e-9, 'a result pins without moving the camera');
  assert.equal(hint(), 'go back to the long record on #1');
  assert.match(map.inspector.innerHTML, /aria-label="Back to the long record on #1 \(Esc\)"><span aria-hidden="true">←<\/span> Back<\/button>/,
    'below the top the head button says Back and names where it goes');
  // Back up the same way: Esc to the paper, its frame as it was...
  map.key('Escape');
  map.advanceTo(map.now() + 2000);
  assert.equal(map.location.hash, '#o=paper%3Aa-long');
  assert.ok(Math.abs(map.view().k - paperView.k) < 1e-9 && Math.abs(map.view().tx - paperView.tx) < 1e-6);
  // ...the card's Back button to the problem, its sector framed again...
  map.inspector.fire('click', {target: {closest: sel => sel === '[data-universe-clear]' ? {} : null}});
  map.advanceTo(map.now() + 2000);
  assert.equal(map.location.hash, '#o=problem%3Ap1');
  assert.ok(Math.abs(map.view().k - sector) < 1e-9, 'the sector frame returns');
  // ...and a click on empty ground to the whole field.
  map.canvas.fire('click', {clientX: 3, clientY: 3, detail: 1});
  map.advanceTo(map.now() + 2000);
  assert.equal(map.location.hash, '');
  assert.ok(Math.abs(map.view().k - fitted) < 1e-9, 'and the whole field');
  // A pin made away from the trail goes back to the view it left.
  click('problem:p2');
  click('statement:a-long#r1');
  assert.equal(map.location.hash, '#o=statement%3Aa-long%23r1');
  assert.equal(hint(), 'close this card', 'a result outside the pinned problem starts a new trail');
  map.key('Escape');
  map.advanceTo(map.now() + 2000);
  assert.equal(map.location.hash, '');
  assert.ok(map.view().k > fitted * 1.3, 'closing it keeps the view');
  map.key('Escape');
  map.advanceTo(map.now() + 2000);
  assert.ok(Math.abs(map.view().k - fitted) < 1e-9, 'and Esc with nothing pinned returns to the whole field');
});

test('leaving the mathematics view lets go of the hover, the pin and the column’s card', async () => {
  const map = await mountStructure({companion: true});
  map.intersect(true);
  map.advanceTo(map.now() + 2000);
  const dot = map.results()[0];
  map.canvas.fire('pointermove', {clientX: dot.x, clientY: dot.y});
  map.canvas.fire('click', {clientX: dot.x, clientY: dot.y, detail: 1});
  assert.ok(map.canvas.classList.contains('is-over'));
  const events = type => map.announced.filter(e => e.type === type);
  assert.ok(events('universe:select').pop().detail, 'the click pinned a result for the column');
  map.atlas('system', 'mathematics');
  assert.equal(events('universe:select').pop().detail, null, 'leaving lets the pin go');
  assert.equal(events('universe:hover').pop().detail, null, 'and the hover');
  assert.ok(!map.canvas.classList.contains('is-over'), 'the pointer state is cleared too');
});

test('under a policy that refuses inline scripts a pin prefetches its paper without speculation rules', async () => {
  const strict = await mountStructure({companion: true, speculation: true,
    csp: "default-src 'self'; script-src 'self'; style-src 'self'"});
  strict.intersect(true);
  strict.advanceTo(strict.now() + 2000);
  let dot = strict.results()[0];
  strict.canvas.fire('click', {clientX: dot.x, clientY: dot.y, detail: 1});
  assert.ok(strict.appended.some(node => node.rel === 'prefetch'), 'the paper is prefetched');
  assert.ok(!strict.appended.some(node => node.type === 'speculationrules'), 'no inline rule set is written for the policy to refuse');
  const open = await mountStructure({companion: true, speculation: true});
  open.intersect(true);
  open.advanceTo(open.now() + 2000);
  dot = open.results()[0];
  open.canvas.fire('click', {clientX: dot.x, clientY: dot.y, detail: 1});
  assert.ok(open.appended.some(node => node.type === 'speculationrules'), 'without such a policy the paper is prerendered as before');
});

test('structure (2026-10-04): every mark a datum, no clock or dial props, words for people', () => {
  // The scale is built from the papers' own sequences, a tick per result.
  assert.match(source, /function buildScale\(\) \{[\s\S]{0,400}?paperSequence/);
  // No sweeping hand, dial or bezel vocabulary survives in the source.
  assert.doesNotMatch(source, /\b(?:chronograph|bezel|minute track|watch|wristwatch|clock hand|dial)s?\b/i);
  // The teaser's caption is a plain sentence, not "kind: label".
  assert.doesNotMatch(source, /\(KIND_LABEL\[n\.kind\] \|\| n\.kind\) \+ ': '/);
});

test('a pinned name plate holds its place while the pointer names other results', async () => {
  const map = await mountStructure({page: true});
  map.advanceTo(map.now() + 2000);
  const a = map.place('statement:a-long#r2'), b = map.place('statement:a-long#r3');
  map.canvas.fire('pointermove', {clientX: a.x, clientY: a.y});
  map.canvas.fire('click', {clientX: a.x, clientY: a.y, detail: 1});
  map.advanceTo(map.now() + 2000);
  const pinned = () => map.labels().find(l => l.text.startsWith('Theorem 2.1 ('));
  const before = pinned();
  assert.ok(before, 'the pinned result names itself on a plate');
  map.canvas.fire('pointermove', {clientX: b.x, clientY: b.y});
  map.advanceTo(map.now() + 2000);
  assert.ok(map.labels().some(l => l.text.startsWith('Theorem 3.1 (')), 'the hovered result has its own plate');
  const after = pinned();
  assert.ok(after && after.x === before.x && after.y === before.y, 'and the pinned plate has not moved');
});

test('a teaser still out of view when its data arrives stays closed, then assembles on first view', async () => {
  const map = await mountStructure();
  // The page opened on the system map, or below the fold: the canvas is
  // reported out of view before the reader ever reaches it.
  map.intersect(false);
  map.advanceTo(map.now() + 1000);
  assert.equal(map.frames.size, 0, 'nothing runs while it waits');
  map.intersect(true);
  assert.ok(map.results().every(a => a.alpha < 0.01), 'its first sight is not the finished field');
  assert.ok(map.frames.size > 0, 'the assembly starts');
  map.advanceTo(map.now() + 2000);
  assert.ok(map.results().every(a => a.alpha > 0.99), 'and ends whole');
  assert.equal(map.frames.size, 0);
});

test('the teaser’s own caption says what the pointer is on in a plain sentence, and nothing once it leaves', async () => {
  const map = await mountStructure();
  map.intersect(true);
  map.advanceTo(map.now() + 2000);
  const dot = map.place('statement:a-long#r1');
  map.canvas.fire('pointermove', {clientX: dot.x, clientY: dot.y});
  assert.equal(map.caption.textContent, 'Theorem 1.1 on #1, replayed by Comparator', 'a result: its number, its problem, its evidence');
  assert.doesNotMatch(map.caption.textContent, /paper result:|statement:|_/, 'no kind prefix, id or field name');
  const problem = map.place('problem:p2');
  map.canvas.fire('pointermove', {clientX: problem.x, clientY: problem.y});
  assert.equal(map.caption.textContent, '#2: Second problem');
  map.canvas.fire('pointermove', {clientX: 3, clientY: 3});
  assert.equal(map.caption.textContent, '', 'empty ground leaves no stale name behind');
  assert.ok(!map.caption.classList.contains('is-shown'));
});

/* Wave 2 (4 October 2026): every name read whole, words for counts, one
   scale spacing, the cursor tied to its dot, walking without a zoom, and
   light kept for the evidence. */
function wave2Data({long = 'Proposition 10.1 (A rational series preserving totient parity and the stated separation properties)'} = {}) {
  return () => {
    const d = structureData();
    const n = d.initial.nodes.find(m => m.id === 'statement:c-long#r1');
    n.label = long;
    n.short = long;
    d.initial.nodes.push({id: 'statement:b-long#md', kind: 'paper_statement', sector: 'p2', side: 'long', line: 99,
      lean_status: 'exact', comparator_status: 'compared', paper: 'papers/b-long.html#md',
      label: 'Theorem 5.6 ([criterion using least common multiples](https://github.com/x/y/blob/z/A.lean#L153))',
      x: 364 * Math.cos(2.3), y: 364 * Math.sin(2.3)});
    return d;
  };
}

test('a long name is read whole on two balanced lines, never cut where the room allows', async () => {
  const map = await mountStructure({page: true, data: wave2Data()});
  map.advanceTo(map.now() + 2000);
  const dot = map.at('statement:c-long#r1');
  map.canvas.fire('pointermove', {clientX: dot.x, clientY: dot.y});
  map.advanceTo(map.now() + 2000);
  const lines = map.labels().filter(l => /Proposition 10\.1|separation properties\)/.test(l.text));
  assert.equal(lines.length, 2, 'the plate sets the name in two lines');
  assert.equal(lines.map(l => l.text).join(' '),
    'Proposition 10.1 (A rational series preserving totient parity and the stated separation properties)', 'whole, no letter cut');
  assert.ok(!map.labels().some(l => l.text.endsWith('…')), 'nothing on the field is shortened');
  const [a, b] = lines;
  assert.ok(Math.abs(a.text.length - b.text.length) <= 12, 'the break makes the two lines nearly equal');
  assert.ok(b.y - a.y > 12 && b.y - a.y < 17 && a.x === b.x, 'one under the other, on one centre');
});

test('a Markdown link in a ledger name is read as its words', async () => {
  const map = await mountStructure({page: true, data: wave2Data()});
  map.advanceTo(map.now() + 2000);
  const dot = map.at('statement:b-long#md');
  map.canvas.fire('pointermove', {clientX: dot.x, clientY: dot.y});
  map.advanceTo(map.now() + 2000);
  const text = map.labels().map(l => l.text).join(' ');
  assert.match(text, /Theorem 5\.6 \(criterion using least common multiples\)/);
  assert.doesNotMatch(text, /\]\(|https?:|github/, 'no link syntax or address reaches the field');
});

test('band counts are said in words: "N of M" on a small ring, "N of M replayed" on the map', async () => {
  const teaser = await mountStructure();
  teaser.intersect(true);
  teaser.advanceTo(teaser.now() + 2000);
  const page = await mountStructure({page: true});
  page.advanceTo(page.now() + 2000);
  for (const map of [teaser, page]) {
    const text = map.labels().map(l => l.text).join('');
    assert.doesNotMatch(text, /\d+\/\d+/, 'no count is set as a fraction');
  }
  assert.match(page.labels().map(l => l.text).join(''), /6of6replayed/, 'the map spells the count out, letter by letter along the ring');
});

test('the scale has one spacing all the way round, each sector’s run centred in it', async () => {
  const map = await mountStructure({page: true});
  map.advanceTo(map.now() + 2000);
  const c = map.centre();
  // A result's tick is short; the mark between two papers is longer.
  const angles = map.ticks().filter(seg => Math.hypot(seg.to[0] - seg.from[0], seg.to[1] - seg.from[1]) < 3)
    .map(seg => Math.atan2(seg.from[1] - c.y, seg.from[0] - c.x)).sort((p, q) => p - q);
  const gaps = angles.slice(1).map((a, i) => a - angles[i]).filter(g => g > 1e-6);
  const pitch = Math.min(...gaps);
  const step = Math.min((-0.74 + 2.4) / 6, (2.4 - 0.74) / 4, 0.6) * 0.95;
  assert.ok(Math.abs(pitch - step) < 1e-6, 'neighbouring ticks stand one spacing apart, in every sector');
  // The four results of the second sector make one run about its middle.
  const second = angles.filter(a => a > 0.74 && a < 2.4);
  assert.equal(second.length, 4);
  // (The harness reads the centre to a hundredth of a pixel.)
  assert.ok(Math.abs((second[0] + second[3]) / 2 - (0.74 + 2.4) / 2) < 1e-3, 'centred in its sector');
  assert.ok(second[0] - 0.74 > step && 2.4 - second[3] > step, 'with clear ground at both ends');
});

test('a pinned result is tied to its cursor by a dotted line that walks with it', async () => {
  const map = await mountStructure({page: true});
  map.advanceTo(map.now() + 2000);
  // The tie: a dotted ink line that ends on the cursor's own angle.
  const tie = () => {
    const c = map.centre(), at = map.cursor();
    if (at === null) return undefined;
    return map.strokes().filter(s => s.dashed && s.style === '#211318' && s.segments.length === 1).map(s => s.segments[0])
      .find(seg => Math.abs(Math.atan2(seg.to[1] - c.y, seg.to[0] - c.x) - at) < 1e-6);
  };
  assert.equal(tie(), undefined, 'no tie without a pin');
  const a = map.at('statement:a-long#r1');
  map.canvas.fire('click', {clientX: a.x, clientY: a.y, detail: 1});
  map.advanceTo(map.now() + 400);
  const t = tie();
  assert.ok(t, 'the pin draws its tie');
  assert.ok(Math.hypot(t.from[0] - a.x, t.from[1] - a.y) < 14, 'from just outside the dot’s reticle');
  const c = map.centre(), end = Math.atan2(t.to[1] - c.y, t.to[0] - c.x);
  assert.ok(Math.abs(end - map.cursor()) < 1e-6, 'to the cursor’s own tick');
  map.key('ArrowRight');
  map.advanceTo(map.now() + 2000);
  const moved = tie(), next = map.at('statement:a-long#r2');
  assert.ok(Math.hypot(moved.from[0] - next.x, moved.from[1] - next.y) < 14, 'the next result takes the tie');
  assert.ok(Math.abs(Math.atan2(moved.to[1] - c.y, moved.to[0] - c.x) - map.cursor()) < 1e-6, 'and it ends on the moved cursor');
});

test('walking a paper keeps the view the reader chose; the camera moves only to bring a result back', async () => {
  const map = await mountStructure({page: true, withInspector: true});
  map.advanceTo(map.now() + 2000);
  const before = map.view();
  const a = map.at('statement:a-long#r1');
  map.canvas.fire('click', {clientX: a.x, clientY: a.y, detail: 1});
  map.advanceTo(map.now() + 2000);
  for (const expected of ['r2', 'r3', 'r4']) {
    map.key('ArrowRight');
    map.advanceTo(map.now() + 2000);
    assert.equal(map.location.hash, '#o=statement%3Aa-long%23' + expected);
  }
  const after = map.view();
  assert.ok(Math.abs(after.k - before.k) < 1e-9 && Math.abs(after.tx - before.tx) < 1e-6, 'no zoom, no pan from the whole field');
  assert.equal(map.frames.size, 0, 'and nothing runs once each step has settled');
});

test('light belongs to the evidence: on paper no glow is drawn round a mark in focus', async () => {
  const map = await mountStructure({page: true});
  map.advanceTo(map.now() + 2000);
  const a = map.at('statement:a-long#r2');
  map.canvas.fire('pointermove', {clientX: a.x, clientY: a.y});
  for (const ms of [40, 120, 240, 600]) {
    map.advanceTo(map.now() + ms);
    assert.equal(map.images(), 0, 'the reticle frames the focus; no lit disc is laid behind it');
  }
});

test('plates wait while the camera moves and arrive once it has settled', async () => {
  const map = await mountStructure({page: true});
  map.advanceTo(map.now() + 2000);
  const p = map.at('paper:a-long');
  map.canvas.fire('pointermove', {clientX: p.x, clientY: p.y});
  map.canvas.fire('click', {clientX: p.x, clientY: p.y, detail: 1});
  map.advanceTo(map.now() + 260);
  assert.ok(!map.labels().some(l => l.text === 'The first long record'), 'mid-move, the paper names itself nowhere');
  map.advanceTo(map.now() + 2000);
  const name = map.labels().find(l => l.text === 'The first long record');
  assert.ok(name && name.alpha > 0.99, 'settled, its plate is there whole');
  assert.equal(map.frames.size, 0);
});

test('a pinned plate keeps off its own band’s title, which names where the reader is', async () => {
  const map = await mountStructure({page: true});
  map.advanceTo(map.now() + 2000);
  for (const id of ['statement:a-long#r1', 'statement:a-long#r2', 'statement:a-long#r4']) {
    const dot = map.at(id);
    map.canvas.fire('click', {clientX: dot.x, clientY: dot.y, detail: 1});
    map.advanceTo(map.now() + 2000);
    const text = map.labels().map(l => l.text).join('');
    assert.match(text, /#1Firstproblem/, `${id}: the band title stays in view`);
    assert.match(text, /6of6replayed/, `${id}: and its count`);
  }
});

test('on a small field the two checkers’ counts both stand, apart, never run together', async () => {
  const data = {initial: {nodes: [
    {id: 'problem:west', kind: 'problem', label: 'West', short: '#1', x: -500, y: 0},
    {id: 'problem:east', kind: 'problem', label: 'East', short: '#2', x: 500, y: 0},
    {id: 'integration:comparator', kind: 'integration_surface', label: 'Comparator', sub: '616 of 689 replayed', x: -87, y: 40},
    {id: 'integration:palomar', kind: 'integration_surface', label: 'Palomar', sub: '616 prepared', x: 87, y: 40},
  ], edges: []}};
  const map = await mount({data, width: 600});
  const replayed = map.labels().find(l => l.text === '616 of 689 replayed');
  const prepared = map.labels().find(l => l.text === '616 prepared');
  assert.ok(replayed && prepared, 'both counts are lettered');
  // The fake face sets six pixels a letter; labels are centred.
  const gap = (prepared.x - prepared.text.length * 3) - (replayed.x + replayed.text.length * 3);
  assert.ok(gap >= 13, `a clear gap between the two (${gap.toFixed(1)}px)`);
});

test('the card’s step bar carries the paper’s scale in small, its cursor on this result', async () => {
  const map = await mount({data: resultCardData(), hash: '#o=statement%3Ap257%23thm%3Aa'});
  await map.settle();
  const cursorAt = () => {
    const m = map.inspector.innerHTML.match(/<path class="universe-step__cursor" d="M([\d.]+) 0V7"\/>/);
    return m ? Number(m[1]) : null;
  };
  assert.match(map.inspector.innerHTML, /Result 1 of 2<svg class="universe-step__scale"[^>]*aria-hidden="true"/,
    'a scale under "Result 1 of 2", hidden from assistive technology (the words say it)');
  assert.equal(cursorAt(), 24, 'the first of two results: the cursor a quarter of the way along');
  const ticks = map.inspector.innerHTML.match(/<path class="universe-step__ticks" d="([^"]*)"/)[1];
  assert.equal((ticks.match(/M/g) || []).length, 2, 'a tick for each result');
  map.inspector.fire('click', {target: {closest: sel => sel === '[data-universe-step]' ? {getAttribute: () => '1'} : null}});
  await map.settle();
  assert.match(map.inspector.innerHTML, /Result 2 of 2/);
  assert.equal(cursorAt(), 72, 'Next moves the card’s cursor with the map’s');
});
