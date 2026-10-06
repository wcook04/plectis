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
    removeAttribute: name => { delete attrs[name]; },
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

// A CSS colour's channels, 0 to 1 ('#rrggbb' or 'rgb(r, g, b)').
function rgbOf(color) {
  const hex = /^#([0-9a-f]{6})$/i.exec(color || '');
  if (hex) return [0, 2, 4].map(i => parseInt(hex[1].slice(i, i + 2), 16) / 255);
  const fn = /^rgba?\(\s*([\d.]+)[\s,]+([\d.]+)[\s,]+([\d.]+)/.exec(color || '');
  return fn ? [+fn[1] / 255, +fn[2] / 255, +fn[3] / 255] : null;
}
// How far apart two colours stand, in sRGB channels.
function colorGap(a, b) {
  const p = rgbOf(a), q = rgbOf(b);
  return Math.hypot(p[0] - q[0], p[1] - q[1], p[2] - q[2]);
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
  const selections = [];
  const explorer = Object.assign(element(), {dispatchEvent: event => selections.push(event)});
  canvas.closest = selector => options.explorer && selector === '[data-explorer]' ? explorer : null;
  const scope = Object.fromEntries(['all', 'short', 'long'].map(value => [value,
    element({'data-universe-scope': value, 'aria-pressed': String(value === 'all')})]));
  const overlap = element(); overlap.checked = false;
  const checking = element(); checking.value = 'all';
  const count = element();
  const inspector = element();
  const scrolled = [];
  if (options.inspectorTop != null) {
    Object.assign(inspector, {getBoundingClientRect: () => ({top: options.inspectorTop}),
      scrollIntoView: opts => { scrolled.push(opts); }});
  }
  const results = element();
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
  const selectors = {'[data-universe-results]': results, '[data-universe-scope]': scope.all, '[data-universe-overlap]': overlap, '[data-universe-checking]': checking, '[data-universe-inspector]': inspector, '[data-universe-count]': count,
    '[data-universe-search]': search, '[data-universe-load-full]': full, ...(options.extraSelectors || {})};
  const document = Object.assign(element(), {
    readyState: 'complete', documentElement: element(), activeElement: null,
    querySelector: s => selectors[s] || null,
    querySelectorAll: s => s === '[data-universe-stage]' ? [stage] : s === '[data-universe-lens]' ? [claims, modules] : s === '[data-universe-scope]' ? Object.values(scope) : [],
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
    CustomEvent: class {constructor(type, init) {this.type = type; Object.assign(this, init);}},
    getComputedStyle: () => ({getPropertyValue: name => name === '--u-edge-hot' ? HOT_EDGE : ''}),
    fetch: async url => { requests.push(url); return {json: async () => data[url]}; },
    setTimeout: fn => { if (options.queueTimers) timers.push(fn); else fn(); return 1; }, clearTimeout() {},
  });
  const settle = () => new Promise(resolve => setImmediate(resolve));
  await settle();
  return {results, scope, overlap, checking, canvas, count, inspector, search, claims, modules, zoom, fit, full, location, window, scrolled,
    document, requests, settle, flushTimers, selections, arcs: () => arcs, strokes: () => strokes, labels: () => labels,
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
  const label = map.labels().find(mark => mark.text === 'Shared claims: #249 and #257');
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
  const SHARED = 'Shared claims: #249 and #257';
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
  // 5 October 2026: nothing in the panel folds; a dense group says its
  // count under its phrase and lists every member, the panel scrolling.
  assert.match(map.inspector.innerHTML, /<span class="universe-link__count">\d+ lean modules<\/span>/,
    'module adjacency says its count under its phrase');
  assert.doesNotMatch(map.inspector.innerHTML, /<details|<summary/, 'no disclosure in the panel');
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
async function mountTeaser({withCompanionHost = true, summary} = {}) {
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
  const replaySummary = element();
  replaySummary.innerHTML = 'Comparator replay coverage across the problems’ papers.';
  const row = element({'data-problem-id': 'erdos_257'});
  const host = Object.assign(element(), {querySelector: s => s.startsWith('li.home-problem') ? row : null});
  const section = Object.assign(element(), {querySelector: s => s === '.home-split__text' ? host : null});
  const stage = Object.assign(element(), {
    querySelector: s => s === 'canvas' ? canvas : s === '.home-universe__legend' ? replaySummary : null,
    querySelectorAll: () => [],
    closest: s => s === 'section' && withCompanionHost ? section : null,
    dispatchEvent: event => { announced.push(event); return true; },
  });
  const appended = [];
  // The landing's way into the full map: the atlas bar's Expand map link.
  const expand = element({href: 'maths/universe.html', 'data-universe-expand': ''});
  const document = Object.assign(element(), {
    readyState: 'complete', documentElement: element(), activeElement: null,
    head: {appendChild: node => { appended.push(node); if (node.onload) node.onload(); }},
    createElement: () => element(),
    querySelector: () => null,
    querySelectorAll: s => s === '[data-universe-stage]' ? [stage] :
      s === 'a[data-universe-expand], .home-universe__open' ? [expand] : [],
  });
  const location = {pathname: '/', search: '', hash: '', href: '/'};
  const window = Object.assign(element(), {
    location, devicePixelRatio: 1, isSecureContext: false,
    // Model a loaded desktop companion: production attach publishes its live layout predicate.
    PlectisUniverseCompanion: {attach(api) { api.sideBySide = () => true; }},
    matchMedia: () => ({matches: true}),
    CustomEvent: class { constructor(type, init) { this.type = type; this.detail = init && init.detail; } },
  });
  const data = {initial: {
    ...(summary ? {statements: {summary}} : {}),
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
  return {canvas, location, announced, appended, dot, expand, replaySummary};
}

test('the landing header shows the replay and result counts from the map edition', async () => {
  const map = await mountTeaser({summary: {statements: 1234, comparator: {compared: 987}}});
  assert.equal(map.replaySummary.innerHTML,
    '<span class="home-universe__specimen">987 of 1,234</span> paper results replayed by Comparator.');
});

test('the landing replay count distinguishes a recorded zero from missing metadata', async () => {
  const zero = await mountTeaser({summary: {statements: 37, comparator: {compared: 0}}});
  assert.match(zero.replaySummary.innerHTML, /0 of 37/);
  const missing = await mountTeaser();
  assert.equal(missing.replaySummary.innerHTML, 'Comparator replay coverage across the problems’ papers.');
});

// The lit threads a paint drew (1.25px), each as its run of pieces.
function threadRuns(map) {
  const pieces = map.strokes().filter(s => s.width === 1.25).flatMap(s => s.segments);
  const runs = [];
  pieces.forEach((seg, i) => {
    const prev = pieces[i - 1];
    if (!prev || prev.to[0] !== seg.from[0] || prev.to[1] !== seg.from[1]) runs.push([]);
    runs[runs.length - 1].push(seg);
  });
  return runs;
}
// Whether a thread's end meets an object: a hair from its disc, or at its
// own name (the harness's face sets six pixels a letter, 15px high).
function endsAt(map, end, disc, name) {
  if (Math.hypot(end[0] - disc.x, end[1] - disc.y) < disc.r + 4) return true;
  const label = map.labels().find(l => l.text === name);
  if (!label) return false;
  const half = label.text.length * 3 + 2 + 4 + 1;
  return end[0] > label.x - half && end[0] < label.x + half && end[1] > label.y - 20 && end[1] < label.y + 9;
}

// A teaser with Comparator and a frame clock the test drives, to follow the
// moment a settled hover plays.
async function mountPulse({reduceMotion = false, extraNodes = [], extraEdges = [], styles = {}} = {}) {
  let arcs = [];
  // The threads and words a paint lays down. Every paint sets the
  // canvas's transform first, so they are cleared there; the frame probes
  // in tools/meta/dissemination/tests splice this harness by text and rely
  // on the two lines above and below keeping their exact words.
  let strokes = [], labels = [], path = [], pen = null;
  const context = new Proxy({
    clearRect() { arcs = []; },
    setTransform() { strokes = []; labels = []; },
    arc(x, y, r) { arcs.push({x, y, r, alpha: context.globalAlpha}); },
    // A disc's ink is the fill or stroke laid on it.
    fill() { if (arcs.length) arcs[arcs.length - 1].fill = context.fillStyle; },
    beginPath() { path = []; pen = null; },
    moveTo(x, y) { pen = [x, y]; },
    lineTo(x, y) { if (pen) path.push({from: pen, to: [x, y]}); pen = [x, y]; },
    stroke() {
      if (arcs.length && !path.length) arcs[arcs.length - 1].stroke = context.strokeStyle;
      strokes.push({style: context.strokeStyle, width: context.lineWidth, segments: path.slice()});
    },
    fillText(text, x, y) { labels.push({text, x, y, font: context.font}); },
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
    edges: [[0, 2], [1, 2], ...extraEdges],
  }};
  vm.runInNewContext(source, {document, window, navigator: {},
    getComputedStyle: () => ({getPropertyValue: name => styles[name] || ''}),
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
  return {canvas, comparator, dot, arcs: () => arcs, strokes: () => strokes, labels: () => labels, frames, advanceTo, now: () => now};
}

test('a settled hover sends one ripple and a bead of light along its thread to Comparator', async () => {
  const map = await mountPulse();
  const {dot, comparator} = map;
  map.canvas.fire('pointermove', {clientX: dot.x, clientY: dot.y});
  const start = map.now();
  const mid = {x: (dot.x + comparator.x) / 2, y: (dot.y + comparator.y) / 2};
  const near = (a, p, tolerance) => Math.hypot(a.x - p.x, a.y - p.y) <= tolerance;
  map.advanceTo(start + 16 + 110 + 310);
  // The thread to Comparator as drawn (on the landing it may bend round a
  // name on its way, 5 October 2026): the run of pieces whose far end
  // meets Comparator, its mark or its own name.
  const toComparator = threadRuns(map).find(run => endsAt(map, run[run.length - 1].to, comparator, 'Comparator'));
  assert.ok(toComparator, 'a thread runs from the result to Comparator');
  const off = a => Math.min(...toComparator.map(seg => {
    const [ax, ay] = seg.from, vx = seg.to[0] - ax, vy = seg.to[1] - ay;
    const t = Math.max(0, Math.min(1, ((a.x - ax) * vx + (a.y - ay) * vy) / (vx * vx + vy * vy || 1)));
    return Math.hypot(ax + vx * t - a.x, ay + vy * t - a.y);
  }));
  const span = Math.hypot(comparator.x - dot.x, comparator.y - dot.y);
  assert.ok(map.arcs().some(a => a.r < dot.r + 2 && off(a) < 1.5 &&
      Math.hypot(a.x - dot.x, a.y - dot.y) > 0.25 * span && Math.hypot(a.x - comparator.x, a.y - comparator.y) > 0.25 * span),
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
  teaser.canvas.fire('click', {clientX: 2, clientY: 2});
  assert.equal(selects().pop().detail, null, 'empty ground lets the pin go');
  assert.equal(teaser.location.href, '/', 'a near miss on empty ground never throws the reader off the landing');
  // Chosen again, a second click on the pinned dot opens the result at its
  // place in its paper, as the full map and the system map do (Will, 5 Oct).
  teaser.canvas.fire('click', {clientX: teaser.dot.x, clientY: teaser.dot.y});
  assert.equal(selects().pop().detail.id, 'statement:p257#thm:a');
  teaser.canvas.fire('click', {clientX: teaser.dot.x, clientY: teaser.dot.y});
  assert.equal(teaser.location.href, 'maths/papers/p257.html#thm:a', 'a second click on the pinned dot opens it');
});

test('the landing’s Expand map keeps the teaser’s kept result, and the whole map when nothing is kept', async () => {
  // 5 October 2026: the atlas bar's persistent link opens the explorer; it
  // carries the result the reader kept on the teaser, as its deep link.
  const teaser = await mountTeaser();
  assert.equal(teaser.expand.getAttribute('href'), 'maths/universe.html');
  teaser.canvas.fire('pointermove', {clientX: teaser.dot.x, clientY: teaser.dot.y});
  teaser.canvas.fire('click', {clientX: teaser.dot.x, clientY: teaser.dot.y});
  assert.equal(teaser.expand.getAttribute('href'), 'maths/universe.html#o=statement%3Ap257%23thm%3Aa');
  teaser.canvas.fire('click', {clientX: 2, clientY: 2});
  assert.equal(teaser.expand.getAttribute('href'), 'maths/universe.html', 'letting the pin go returns the whole map');
});

test('nothing the map reads is cut short: no clamp, no cut quote, a box that scrolls instead', () => {
  // 5 October 2026 (Type B design review, endorsed by Will): selecting #68 on
  // the landing showed its short paper's précis stopping mid-line above empty
  // space (a three-line clamp under an overflow-hidden card), and the map's
  // hover preview clamped its body at six lines.
  const strip = text => text.replace(/\/\*[\s\S]*?\*\//g, '');
  const companionCss = strip(readFileSync(new URL('../../../tools/meta/dissemination/maths_site_assets/universe-companion.css', import.meta.url), 'utf8'));
  const mathsCss = strip(readFileSync(new URL('../../../tools/meta/dissemination/maths_site_assets/maths.css', import.meta.url), 'utf8'));
  const companionJs = readFileSync(new URL('../../../tools/meta/dissemination/maths_site_assets/universe-companion.js', import.meta.url), 'utf8');
  for (const [name, css] of [['universe-companion.css', companionCss], ['maths.css', mathsCss]]) {
    assert.doesNotMatch(css, /line-clamp/, `${name} clamps no text`);
  }
  assert.match(companionCss, /\.uc \{[^}]*overflow-y: auto/, 'the companion scrolls inside its own box');
  assert.doesNotMatch(companionCss, /\.uc__focus \{[^}]*overflow: hidden/, 'the card slot never crops its card');
  assert.doesNotMatch(companionCss, /\.uc__quote \{[^}]*max-height/, 'a result is quoted whole');
  assert.doesNotMatch(companionJs, /The statement continues in the paper|function fitQuote/, 'no quote is trimmed');
  assert.doesNotMatch(mathsCss, /is-preview[^{]*\{[^}]*(?:max-height|mask-image)/, 'a preview is never faded off');
});

test('a pinned result keeps the column when the pointer leaves; a click elsewhere lets it go', () => {
  const companion = readFileSync(new URL('../../../tools/meta/dissemination/maths_site_assets/universe-companion.js', import.meta.url), 'utf8');
  const off = companion.slice(companion.indexOf('function pointerOff()'));
  assert.match(off.slice(0, 400), /if \(state\.keyboard \|\| state\.pinned\) return;\s*later\('leave', close, LEAVE\)/,
    'leaving the column and the drawing must not close a pinned card (Will, 4 Oct)');
  assert.match(companion, /addEventListener\('pointerdown'[\s\S]{0,240}state\.pinned[\s\S]{0,240}close\(\)/,
    'a click outside the column and the drawing lets a pinned card go');
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
  assert.match(source, /new IntersectionObserver\(function \(entries\) \{[\s\S]{0,500}?seen\.disconnect\(\);\s*startReveal\(\);/);
  // At first look a drawing just under the fold counts as on the first
  // screen (5 October 2026: at 1280 by 690 the card's frame showed empty).
  assert.match(source, /var near = firstLook && box && port && box\.top < port\.bottom \+ port\.height/);
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
  const far = () => map.arcs().filter(a => a.x < map.dot.x && a.y > map.dot.y + 20 && a.fill)
    .reduce((best, a) => (best && best.r >= a.r ? best : a), null);
  // On the landing a mark drops back by its ink, toward the ground the
  // canvas is seen on (here the harness's surface colour), never by
  // turning transparent (5 October 2026).
  const GROUND = '#fffdf7';
  const toGround = () => colorGap(far().fill, GROUND);
  const rest = far(), restGap = toGround();
  map.canvas.fire('pointermove', {clientX: map.dot.x, clientY: map.dot.y});
  map.advanceTo(map.now() + 400);
  const dimGap = toGround();
  assert.ok(dimGap < restGap - 0.1, 'a result in focus fades the unconnected paper toward the ground');
  assert.equal(far().alpha, rest.alpha, 'faded ink, never made transparent');
  map.canvas.fire('pointermove', {clientX: 2, clientY: 2});
  map.advanceTo(map.now() + 48);
  assert.ok(toGround() < restGap - 0.1, 'the gap after a dot holds the dim instead of snapping the field bright');
  map.canvas.fire('pointermove', {clientX: map.dot.x, clientY: map.dot.y});
  map.advanceTo(map.now() + 32);
  assert.ok(toGround() <= dimGap + 0.02, 'the next dot carries on from the held dim, never restarting from nothing');
  map.canvas.fire('pointermove', {clientX: 2, clientY: 2});
  map.advanceTo(map.now() + 900);
  assert.ok(Math.abs(toGround() - restGap) < 0.02, 'once the pointer has really left, the field eases back');
  assert.equal(map.frames.size, 0, 'and nothing keeps running');
});

test('on the landing what drops back keeps its hue: its own ink faded, never a neutral grey', async () => {
  // The night scheme's tokens: Comparator's orange on the violet ground.
  const styles = {'--u-integration': '#e08a58', '--surface': '#272132', '--ink': '#f2e6d4',
                  '--faint': '#a6a2b1', '--muted': '#bcb8c6'};
  // A replayed result of another problem, far from the one in focus.
  const other = {id: 'statement:p68#thm:x', kind: 'paper_statement', label: 'Theorem 9.9', x: -150, y: 150,
                 sector: 'erdos_68', lean_status: 'exact', comparator_status: 'compared', side: 'short'};
  const map = await mountPulse({styles, extraNodes: [other]});
  const theirs = () => map.arcs().filter(a => a.x < map.dot.x - 100 && a.y > map.dot.y + 20 && a.fill)
    .reduce((best, a) => (best && best.r >= a.r ? best : a), null);
  assert.equal(theirs().fill, '#e08a58', 'at rest a replayed result wears Comparator’s colour');
  map.canvas.fire('pointermove', {clientX: map.dot.x, clientY: map.dot.y});
  map.advanceTo(map.now() + 400);
  const faded = theirs().fill;
  assert.notEqual(faded, '#a6a2b1', 'it does not turn the faint grey');
  const [r, , b] = rgbOf(faded);
  assert.ok(r - b > 0.04, `still warm, its own orange faded (${faded}); the grey it used to turn was cool`);
  assert.ok(colorGap(faded, '#272132') < colorGap('#e08a58', '#272132') - 0.15, 'and it sinks toward the ground');
  assert.equal(theirs().alpha, 1, 'drawn whole: the mix is in the ink, as color-mix(in oklab) is on the system map');
});

test('a lit thread goes round a problem in its way instead of through it', async () => {
  // A problem set on the straight line from the result to Comparator: a line
  // through its mark would read as a relation to it that the data lacks.
  const between = {id: 'problem:erdos_68', kind: 'problem', label: 'Factorial series', short: '#68',
                   x: 75, y: -75, sector: 'erdos_68'};
  const map = await mountPulse({extraNodes: [between]});
  const mid = {x: (map.dot.x + map.comparator.x) / 2, y: (map.dot.y + map.comparator.y) / 2};
  const disc = map.arcs().filter(a => Math.hypot(a.x - mid.x, a.y - mid.y) < 1 && a.r > 4)
    .reduce((best, a) => (best && best.r >= a.r ? best : a), null);
  assert.ok(disc, 'the problem stands on the straight way');
  map.canvas.fire('pointermove', {clientX: map.dot.x, clientY: map.dot.y});
  map.advanceTo(map.now() + 2400);
  const threads = map.strokes().filter(s => s.width === 1.25 && s.segments.length).flatMap(s => s.segments);
  assert.ok(threads.length >= 2, 'the result’s threads are drawn');
  // Distance from the problem's centre to a piece of thread.
  const away = seg => {
    const [ax, ay] = seg.from, [bx, by] = seg.to, vx = bx - ax, vy = by - ay;
    const t = Math.max(0, Math.min(1, ((disc.x - ax) * vx + (disc.y - ay) * vy) / (vx * vx + vy * vy || 1)));
    return Math.hypot(ax + vx * t - disc.x, ay + vy * t - disc.y);
  };
  assert.ok(threads.every(seg => away(seg) > disc.r + 4),
    'every thread keeps clear of the problem’s mark (its disc and four pixels more)');
  const reachesComparator = threadRuns(map).some(run => endsAt(map, run[run.length - 1].to, map.comparator, 'Comparator'));
  assert.ok(reachesComparator, 'and the thread to Comparator still reaches it, at its mark or its name');
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
  withInspector = false, data = structureData, styles = {}, reads = false, keyRow = false} = {}) {
  let arcs = [], strokes = [], fills = [], rects = [], labels = [], path = [], pen = null, paints = 0, dash = [], images = 0;
  // Where the drawing has moved its origin (translate, save and restore;
  // a rotation turns a letter about its own place, which is all a label's
  // place needs).
  let origin = [0, 0];
  const saved = [];
  const context = new Proxy({
    clearRect() { arcs = []; strokes = []; fills = []; rects = []; labels = []; images = 0; paints++; },
    setTransform() { origin = [0, 0]; },
    save() { saved.push(origin.slice()); },
    restore() { origin = saved.pop() || [0, 0]; },
    translate(x, y) { origin = [origin[0] + x, origin[1] + y]; },
    beginPath() { path = []; pen = null; },
    moveTo(x, y) { pen = [x, y]; },
    lineTo(x, y) { if (pen) path.push({from: pen, to: [x, y]}); pen = [x, y]; },
    setLineDash(segments) { dash = segments; },
    stroke() { strokes.push({style: context.strokeStyle, alpha: context.globalAlpha, width: context.lineWidth, dashed: dash.length > 0, segments: path.slice()}); },
    fill() {
      fills.push({style: context.fillStyle, alpha: context.globalAlpha});
      if (arcs.length) arcs[arcs.length - 1].fill = context.fillStyle;
    },
    fillRect(x, y, w, h) { rects.push({x, y, w, h, alpha: context.globalAlpha, style: context.fillStyle}); },
    arc(x, y, r, a0, a1) { arcs.push({x, y, r, a0, a1, alpha: context.globalAlpha}); },
    drawImage() { images++; },
    measureText(text) { return {width: String(text).length * 6}; },
    fillText(text, x, y) {
      labels.push({text, x: x + origin[0], y: y + origin[1], alpha: context.globalAlpha, font: context.font, fill: context.fillStyle,
                   align: context.textAlign, baseline: context.textBaseline});
    },
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
  // An element that can hold others, as the key's slot and list are.
  const container = () => Object.assign(element(), {
    children: [], clientWidth: 400,
    appendChild(node) { this.children.push(node); node.parentNode = this; return node; },
    insertBefore(node, ref) {
      const at = this.children.indexOf(ref);
      if (node.parentNode && node.parentNode.children) node.parentNode.children.splice(node.parentNode.children.indexOf(node), 1);
      this.children.splice(at < 0 ? this.children.length : at, 0, node);
      node.parentNode = this;
      return node;
    },
  });
  const caption = element();
  // The landing's caption row under the drawing: the caption and the buttons.
  const captionRow = keyRow ? container() : null;
  if (captionRow) { captionRow.classList.add('home-universe__caption'); captionRow.appendChild(caption); }
  const captured = {};
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
    head: {appendChild: node => { appended.push(node); if (node.onload) node.onload(); }},
    createElement: () => (keyRow ? container() : element()),
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
    // Model a loaded desktop companion: production attach publishes its live
    // layout predicate (and, once its data is in, whether it reads a sector).
    PlectisUniverseCompanion: {attach(api) {
      api.sideBySide = () => true;
      if (reads) api.reads = () => true;
      captured.api = api;
    }},
    history: {replaceState(_a, _b, url) { location.hash = new URL(url, 'http://test').hash; }},
    matchMedia: query => ({matches: /reduce/.test(query) ? reduceMotion : true}),
    requestAnimationFrame: fn => { rafCalls++; frames.set(nextFrame, fn); return nextFrame++; },
    cancelAnimationFrame: id => { frames.delete(id); },
    IntersectionObserver: IO, CustomEvent,
  });
  const sandbox = {document, window, navigator: {}, CustomEvent, IntersectionObserver: IO, URL,
    getComputedStyle: () => ({getPropertyValue: name => styles[name] || ''}),
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
  return {canvas, caption, captionRow, document, window, location, announced, appended, frames, advanceTo, now: () => now,
    rafCalls: () => rafCalls, paints: () => paints, arcs: () => arcs, rects: () => rects, labels: () => labels,
    strokes: () => strokes, fills: () => fills, images: () => images, inspector, centre, place, view, at, results, cursor, ticks,
    api: () => captured.api,
    intersect(on, ratio = on ? 1 : 0) { for (const o of observers) if (!o.gone) o.callback([{isIntersecting: on, intersectionRatio: ratio, target: o.target}]); },
    // The opening's first callback for a drawing out of view, with where it
    // stands (the paint observer, 120px wider, still has it on screen).
    firstLook(box, port) { for (const o of observers) if (!o.gone && o.options && o.options.threshold) o.callback([{isIntersecting: false, intersectionRatio: 0, target: o.target, boundingClientRect: box, rootBounds: port}]); },
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
  // The results ring is laid by a pen running once round it (6 October
  // 2026): part way round, the results it has passed are set and the rest
  // are still to come.
  const polar = () => {
    const c = map.centre();
    return map.results().map(a => ({ang: Math.atan2(a.y - c.y, a.x - c.x), d: Math.hypot(a.x - c.x, a.y - c.y), alpha: a.alpha}));
  };
  map.advanceTo(start + 16 + 470);
  const seating = polar();
  assert.ok(seating.length > 0, 'the pen has begun to lay the results ring');
  assert.ok(seating.some(a => a.alpha > 0.1 && a.alpha < 0.9), 'the results ring is arriving');
  map.advanceTo(start + 2000);
  assert.equal(map.frames.size, 0, 'the opening ends and nothing keeps running');
  const final = polar();
  assert.ok(seating.length < final.length, 'part way round, part of the ring is still to come');
  assert.ok(seating.every(m => {
    const f = final.find(q => Math.abs(q.ang - m.ang) < 1e-6);
    return f && m.d < f.d - 0.05;
  }), 'arriving, the ring stood inside its place and seated outward');
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
  assert.equal(hint(), 'go back to the long paper on #1');
  assert.match(map.inspector.innerHTML, /aria-label="Back to the long paper on #1 \(Esc\)"><span aria-hidden="true">←<\/span> Back<\/button>/,
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

test('the panel reads a problem, its results in paper order, then a result under one line naming its problem', async () => {
  // 5 October 2026 (the explorer): a chosen problem reads its question and
  // its results, short paper first, each paper in its own order; a result
  // chosen from that list goes a level down, its problem shrinking to one
  // line above it, and going back returns to the problem. Nothing folds.
  const map = await mountStructure({page: true, withInspector: true});
  map.advanceTo(map.now() + 2000);
  const p = map.at('problem:p1');
  map.canvas.fire('click', {clientX: p.x, clientY: p.y, detail: 1});
  map.advanceTo(map.now() + 2000);
  const html = map.inspector.innerHTML;
  assert.match(html, /Erdős problem #1/);
  assert.match(html, /<h2 class="universe-inspector__title universe-inspector__title--problem">First problem<\/h2>/);
  assert.match(html, /All 6 of its results are replayed by Comparator\./, 'the count is said in words');
  const rows = [...html.matchAll(/class="universe-item" data-universe-go="(\d+)"[\s\S]*?universe-item__num">([^<]*)<\/span><span class="universe-item__name">([^<]*)</g)];
  assert.deepEqual(rows.map(m => m[3]), ['Result 1 of a-short', 'Result 2 of a-short',
    'Result 1 of a-long', 'Result 2 of a-long', 'Result 3 of a-long', 'Result 4 of a-long'],
    'the short paper first, then the long record, each in the order it states them');
  assert.doesNotMatch(html, /<details|<summary/, 'no disclosure in the panel');
  const chosen = rows[3][1];
  map.inspector.fire('click', {target: {closest: s => s === '[data-universe-go]' ? {getAttribute: () => chosen} : null}});
  map.advanceTo(map.now() + 2000);
  assert.equal(map.location.hash, '#o=statement%3Aa-long%23r2');
  assert.match(map.inspector.innerHTML,
    /^<p class="universe-context"><button type="button" class="universe-context__go" data-universe-go="\d+">Erdős #1<\/button><span class="universe-context__title">First problem<\/span><\/p>/,
    'the problem shrinks to one line over the result');
  assert.match(map.inspector.innerHTML, /click empty ground to go back to #1\./);
  map.key('Escape');
  map.advanceTo(map.now() + 2000);
  assert.equal(map.location.hash, '#o=problem%3Ap1', 'back up to the problem it was chosen from');
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
  assert.ok(!open.appended.some(node => node.type === 'speculationrules'), 'a pin never starts rendering a second document');
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

test('a teaser partly on the first screen opens at once; reached by scrolling it waits for a third', async () => {
  // 5 October 2026: the map moved up onto the landing's first screen, where a
  // third of it or less shows, and a reader who had not scrolled met an empty
  // frame while the opening waited for 35 per cent of the drawing.
  const first = await mountStructure();
  first.intersect(true, 0.2);
  first.advanceTo(first.now() + 2000);
  assert.ok(first.results().every(a => a.alpha > 0.99), 'partly in view at first look, it opens and ends whole');
  const below = await mountStructure();
  below.intersect(false);
  below.intersect(true, 0.1);
  below.advanceTo(below.now() + 1000);
  assert.ok(below.results().every(a => a.alpha < 0.01), 'a sliver reached by scrolling waits closed');
  below.intersect(true, 0.4);
  below.advanceTo(below.now() + 2000);
  assert.ok(below.results().every(a => a.alpha > 0.99), 'a third in view opens it');
});

test('at first look a teaser just under the fold opens at once; further down it still waits', async () => {
  // 5 October 2026: at 1280 by 690 the card's frame was on the first screen
  // while its canvas, a few pixels lower, waited closed: an empty frame.
  const near = await mountStructure();
  near.firstLook({top: 700, bottom: 1200}, {top: 0, bottom: 690, height: 690});
  near.advanceTo(near.now() + 2000);
  assert.ok(near.results().every(a => a.alpha > 0.99), 'within a screen of the fold it opens and ends whole');
  const far = await mountStructure();
  far.firstLook({top: 1600, bottom: 2100}, {top: 0, bottom: 690, height: 690});
  far.advanceTo(far.now() + 1000);
  assert.ok(far.results().every(a => a.alpha < 0.01), 'further down it waits closed for the reader');
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


test('publication scope and verification compose without inventing statement equivalence', async () => {
  const decl = (name, file) => ({name, file, href: 'https://example.org/' + file});
  const row = (paper, side, num, declarations = [], proof = false) => ({
    id: `statement:${paper}#thm:${num}`, kind: 'paper_statement', label: `Theorem ${num} (Fixture)`,
    paper_id: paper, side, sector: 'one', x: num * 20, y: 50, declarations,
    lean_status: declarations.length ? 'exact' : 'none',
    comparator_status: declarations.length ? 'compared' : 'not_applicable',
    proof_status: proof ? 'ordinary_proof' : null,
    proof_note: proof ? 'Reviewed ordinary proof; independent human review not recorded.' : null,
  });
  const nodes = [
    {id: 'problem:one', kind: 'problem', label: 'Programme', sector: 'one', x: -100, y: 0},
    row('short', 'short', 1, [decl('N.shared', 'A.lean')]),
    row('long', 'long', 2, [decl('N.shared', 'A.lean')]),
    row('long', 'long', 3, [decl('N.shared', 'B.lean')]),
    row('long', 'long', 4, [], true),
    row('short', 'short', 5),
    row('long', 'long', 5), // same label alone is not overlap
  ];
  const data = {initial: {nodes, edges: [], bands: [
    {sector: 'one', title: 'Programme', lo: 0, hi: 1, rings: {}, evidence: {replayed: 3, none: 3}},
  ]}, graph: {nodes, edges: []},
    layout: {positions: Object.fromEntries(nodes.map(n => [n.id, [n.x, n.y]])),
      sectors: Object.fromEntries(nodes.map(n => [n.id, ['one', 'fixture']]))}};
  const map = await mount({data});
  assert.equal(map.count.textContent, '7 shown');
  map.scope.short.fire('click');
  assert.equal(map.count.textContent, '3 of 7 shown');
  assert.equal(map.scope.short.getAttribute('aria-pressed'), 'true');
  assert.equal(map.scope.long.getAttribute('aria-pressed'), 'false');
  assert.match(map.inspector.innerHTML, /<b>1<\/b> of 2 results replayed/);
  map.overlap.checked = true; map.overlap.fire('change');
  assert.equal(map.count.textContent, '2 of 7 shown');
  map.scope.all.fire('click');
  assert.equal(map.count.textContent, '3 of 7 shown', 'only file-qualified shared support links');
  map.full.fire('click'); await map.settle();
  assert.equal(map.count.textContent, '3 of 7 shown', 'full graph preserves scope and file-qualified overlap');
  map.overlap.checked = false; map.overlap.fire('change');
  map.checking.value = 'ordinary_proof'; map.checking.fire('change');
  assert.equal(map.count.textContent, '2 of 7 shown', 'missing Lean alone is not an ordinary proof');
  assert.match(map.inspector.innerHTML, /<b>0<\/b> of 1 result replayed/);
  map.scope.short.fire('click');
  assert.match(map.inspector.innerHTML, /No paper results match these filters/);
  map.scope.all.fire('click');
  map.search.value = 'ordinary proof'; map.search.fire('input'); map.search.fire('keydown', {key: 'Enter'});
  assert.match(map.inspector.innerHTML, /Ordinary proof in the paper/);
  assert.match(map.inspector.innerHTML, /independent human review not recorded/);
  assert.match(map.inspector.innerHTML, /No Lean statement/);
  map.search.value = ''; map.search.fire('input');
  map.checking.value = 'replayed'; map.checking.fire('change');
  assert.equal(map.count.textContent, '4 of 7 shown');
});


test('walking filtered results skips hidden statements and search keeps proof symbols', async () => {
  const nodes = [1, 2, 3].map(number => ({
    id: `statement:long#thm:${number}`, kind: 'paper_statement', label: `Theorem ${number} (Fixture)`,
    x: number * 20, y: 50, side: 'long', line: number, lean_status: 'none',
    proof_status: number === 2 ? null : 'ordinary_proof', proof_note: 'Reviewed ordinary proof.',
  }));
  const map = await mount({data: {initial: {nodes, edges: []}}, hash: '#o=statement%3Along%23thm%3A1'});
  map.checking.value = 'ordinary_proof'; map.checking.fire('change');
  map.document.fire('keydown', {key: 'ArrowRight', target: {tagName: 'SELECT'}});
  assert.equal(map.location.hash, '#o=statement%3Along%23thm%3A1', 'native selector keys do not walk the canvas');
  map.document.fire('keydown', {key: 'ArrowRight'});
  assert.equal(map.location.hash, '#o=statement%3Along%23thm%3A3', 'skip hidden result two');
  assert.match(map.inspector.innerHTML, /data-universe-step="1" disabled/);
  map.document.fire('keydown', {key: 'ArrowRight'});
  assert.equal(map.location.hash, '#o=statement%3Along%23thm%3A3');
  map.document.fire('keydown', {key: 'ArrowLeft'});
  assert.equal(map.location.hash, '#o=statement%3Along%23thm%3A1');
  assert.match(map.inspector.innerHTML, /data-universe-step="-1" disabled/);
  map.document.activeElement = map.search;
  map.search.value = 'ordinary proof'; map.search.fire('input');
  assert.equal((map.results.innerHTML.match(/glyph--ordinary_proof/g) || []).length, 2);
  assert.doesNotMatch(map.results.innerHTML, /glyph--none/);
});

/* The teaser pass (5 October 2026): nothing crowds the card's edge, the
   words are near body size, threads go round words, a kept result looks
   kept, the column changes without double exposure, the field dims in its
   own hues, and a key stands in the caption slot at rest. */

// A label's extent on the field, from its place, its face and how it was
// set (the harness's face sets six pixels a letter).
function labelExtent(label) {
  const size = Number((/(\d+(?:\.\d+)?)px/.exec(label.font || '') || [0, 12])[1]);
  const width = label.text.length * 6;
  const x0 = label.align === 'left' ? label.x : label.align === 'right' ? label.x - width : label.x - width / 2;
  const y0 = label.baseline === 'middle' ? label.y - size / 2 : label.y - size * 0.75;
  return {x0, x1: x0 + width, y0, y1: y0 + size, size};
}

test('on the landing the teaser’s outermost words keep 32px from the card’s edge, and none is under 12px', async () => {
  const map = await mountStructure();
  map.intersect(true);
  map.advanceTo(map.now() + 2000);
  const words = map.labels().filter(l => l.alpha > 0.05);
  assert.ok(words.length > 10, 'the ring is lettered');
  const edge = Math.min(...words.map(l => {
    const e = labelExtent(l);
    return Math.min(e.x0, e.y0, map.canvas.clientWidth - e.x1, map.canvas.clientHeight - e.y1);
  }));
  assert.ok(edge >= 31, `the outermost word stands ${edge.toFixed(1)}px from the frame`);
  assert.ok(words.every(l => labelExtent(l).size >= 12), 'nothing on the field is set under 12px');
  assert.ok(words.some(l => /^600 16px/.test(l.font)) && words.some(l => /^400 14px/.test(l.font)),
    'band titles at 16px and their counts at 14px, near the body size beside them');
  // The title at three o'clock is set level, not turned on its side.
  const level = words.find(l => l.text === '#3');
  assert.ok(level && level.align === 'left', 'the title at three o’clock reads level, out beside the scale');
  // A hovered result's plate: the plate face, its box clear of the edge.
  const dot = map.place('statement:c-long#r1');
  map.canvas.fire('pointermove', {clientX: dot.x, clientY: dot.y});
  map.advanceTo(map.now() + 2000);
  const plate = map.labels().find(l => l.text.startsWith('Theorem 1.1'));
  assert.ok(plate && /^500 15px/.test(plate.font), 'a name plate is set at 15px');
  const box = labelExtent(plate);
  assert.ok(box.x1 + 9 <= map.canvas.clientWidth - 24 && box.x0 - 9 >= 24,
    'the plate’s box keeps 24px from the canvas, clear of the corner marks');
});

test('the map’s own page keeps its smaller type and its old edge', async () => {
  const map = await mountStructure({page: true});
  map.advanceTo(map.now() + 2000);
  assert.ok(map.labels().some(l => /^600 12px/.test(l.font || '')), 'the page’s band titles stay at 12px');
  assert.ok(!map.labels().some(l => /^600 16px/.test(l.font || '')), 'the teaser’s set is the teaser’s alone');
});

test('a kept result is framed in ember; one under the pointer stays in ink', async () => {
  const INK = '#f2e6d4', EMBER = '#e18a79';
  const map = await mountStructure({companion: true, styles: {'--ink': INK, '--home-ember': EMBER}});
  map.intersect(true);
  map.advanceTo(map.now() + 2000);
  const a = map.place('statement:a-long#r2'), b = map.place('statement:b-long#r3');
  const frame = (p, ink) => map.rects().filter(r => r.style === ink &&
    Math.abs(r.x + r.w / 2 - p.x) < 24 && Math.abs(r.y + r.h / 2 - p.y) < 24);
  map.canvas.fire('pointermove', {clientX: a.x, clientY: a.y});
  map.advanceTo(map.now() + 600);
  assert.ok(frame(a, INK).length >= 8, 'pointed at, its four corners are ink');
  assert.equal(frame(a, EMBER).length, 0, 'and none is ember');
  map.canvas.fire('click', {clientX: a.x, clientY: a.y, detail: 1});
  map.advanceTo(map.now() + 600);
  assert.ok(frame(a, EMBER).length >= 8, 'kept, its frame turns ember');
  assert.ok(map.strokes().some(s => s.style === EMBER && !s.segments.length), 'and so does its ring');
  map.canvas.fire('pointermove', {clientX: b.x, clientY: b.y});
  map.advanceTo(map.now() + 600);
  assert.ok(frame(a, EMBER).length >= 8, 'it stays ember while another result is pointed at');
  assert.ok(frame(b, INK).length >= 8 && !frame(b, EMBER).length, 'which is framed in ink');
});

test('beside a column that reads the result whole, its plate gives the paper’s number only', async () => {
  const map = await mountStructure({companion: true, reads: true});
  map.intersect(true);
  map.advanceTo(map.now() + 2000);
  const a = map.place('statement:a-long#r2');
  map.canvas.fire('pointermove', {clientX: a.x, clientY: a.y});
  map.advanceTo(map.now() + 600);
  const texts = map.labels().map(l => l.text);
  assert.ok(texts.includes('Theorem 2.1'), 'the plate names the result by its number');
  assert.ok(!texts.some(t => /Result 2 of a-long/.test(t)), 'and leaves its title to the column');
  // Kept, and another result pointed at: the column holds the kept one, so
  // the other is named in full.
  map.canvas.fire('click', {clientX: a.x, clientY: a.y, detail: 1});
  const b = map.place('statement:a-long#r4');
  map.canvas.fire('pointermove', {clientX: b.x, clientY: b.y});
  map.advanceTo(map.now() + 600);
  assert.ok(map.labels().some(l => /Theorem 4\.1 \(Result 4 of a-long\)|Result 4 of a-long/.test(l.text)),
    'a result the column is not showing is named in full');
});

test('the lit sector is indexed by hairlines, not washed, and they stop short of words', async () => {
  const map = await mountStructure();
  map.intersect(true);
  map.advanceTo(map.now() + 2000);
  const a = map.place('statement:a-long#r2');
  map.canvas.fire('pointermove', {clientX: a.x, clientY: a.y});
  map.advanceTo(map.now() + 600);
  // The harness's halo colour is the stylesheet's fallback for --u-halo.
  assert.ok(!map.fills().some(f => f.style === 'rgba(226,168,62,0.35)'), 'no wash is laid over the sector');
  const index = map.strokes().filter(s => s.style === '#211318' && Math.abs(s.alpha - 0.55) < 0.01).flatMap(s => s.segments);
  assert.ok(index.length > 4, 'two edges and an arc index the sector');
  const letters = map.labels().filter(l => l.text.length === 1 && l.alpha > 0.05);
  const gap = Math.min(...index.flatMap(seg => letters.map(l => Math.min(
    Math.hypot(seg.from[0] - l.x, seg.from[1] - l.y), Math.hypot(seg.to[0] - l.x, seg.to[1] - l.y)))));
  assert.ok(gap >= 6, `the index keeps clear of the sector’s title (${gap.toFixed(1)}px)`);
  const page = await mountStructure({page: true});
  page.advanceTo(page.now() + 2000);
  const p = page.at('statement:a-long#r2');
  page.canvas.fire('pointermove', {clientX: p.x, clientY: p.y});
  page.advanceTo(page.now() + 600);
  assert.ok(page.fills().some(f => f.style === 'rgba(226,168,62,0.35)'), 'the map’s own page keeps its lit slice');
});

test('letting the column go restores the field on the column’s beat, with no hold', async () => {
  const map = await mountStructure({companion: true});
  map.intersect(true);
  map.advanceTo(map.now() + 2000);
  const api = map.api();
  const other = map.place('statement:b-long#r2');
  const ink = () => map.arcs().filter(a => Math.hypot(a.x - other.x, a.y - other.y) < 1 && a.fill)
    .reduce((best, a) => (best && best.r >= a.r ? best : a), null).fill;
  const rest = ink();
  api.light('p1');
  map.advanceTo(map.now() + 600);
  assert.notEqual(ink(), rest, 'the column reading #1 drops the other sector back');
  api.light(null);
  map.advanceTo(map.now() + 16 + 160 + 16);
  assert.equal(ink(), rest, 'the column closing brings it back within its own 160ms');
});

test('at rest the caption slot holds a key of the map’s own marks, which steps out while a name shows', async () => {
  const map = await mountStructure({keyRow: true});
  map.intersect(true);
  map.advanceTo(map.now() + 2000);
  const slot = map.captionRow.children.find(node => node.className === 'universe-captionslot');
  assert.ok(slot, 'the caption shares its slot with the key');
  const key = slot.children.find(node => node.className === 'universe-key');
  assert.ok(key, 'the key is there at rest');
  for (const words of ['Replayed by Comparator', 'Replay queued', 'No Lean statement', 'Checked claim']) {
    assert.match(key.innerHTML, new RegExp(words), `it names: ${words}`);
  }
  assert.doesNotMatch(key.innerHTML, /·|·/, 'plain words, no middle dots');
  assert.match(key.innerHTML, /universe-key__mark--replayed[\s\S]*universe-key__mark--lean/, 'each drawn with the map’s mark');
  const dot = map.place('statement:a-long#r1');
  map.canvas.fire('pointermove', {clientX: dot.x, clientY: dot.y});
  assert.ok(key.classList.contains('is-out'), 'it steps out while the caption names the result');
  map.canvas.fire('pointermove', {clientX: 3, clientY: 3});
  assert.ok(!key.classList.contains('is-out'), 'and comes back when the caption is empty');
});

test('the column and the drawing’s card never show at once: out in 90ms, then the title travels; away in 160ms, then the list', () => {
  const css = readFileSync(new URL('../../../tools/meta/dissemination/maths_site_assets/universe-companion.css', import.meta.url), 'utf8');
  const js = readFileSync(new URL('../../../tools/meta/dissemination/maths_site_assets/universe-companion.js', import.meta.url), 'utf8');
  assert.match(css, /\.uc-host--open > :not\(\.uc\) \{[^}]*transition: opacity 90ms/, 'the list steps out in 90ms');
  assert.match(css, /\.uc-host > :not\(\.uc\) \{[^}]*transition: opacity 240ms [^;]*\) 160ms;/,
    'and comes back over 240ms only after the card has gone (160ms)');
  assert.match(css, /\.uc \{[^}]*transition: opacity 160ms/, 'the card steps out in 160ms');
  assert.match(css, /\.uc\.is-open \{[^}]*transition: opacity 0s linear 90ms/, 'and shows only once the list has gone');
  assert.match(js, /var OUT = 90, AWAY = 160;/);
  assert.match(js, /\{ duration: 320, delay: OUT, easing: EASE, fill: 'backwards' \}/, 'the title travels only after OUT');
  assert.match(js, /var EASE = 'cubic-bezier\(0\.16, 1, 0\.3, 1\)';/, 'arrivals ease out hard');
  assert.doesNotMatch(css.replace(/\/\*[\s\S]*?\*\//g, ''), /transition:[^;]*(?:width|height|top|left|margin)\b/,
    'only opacity and transform move (the fold excepted, by its rows)');
  assert.match(js, /Kept\. Esc lets it go/, 'a kept card says so in plain words');
});

test('URL and search selections notify the explorer reading owner', async () => {
  const map = await mount({explorer: true, hash: '#o=claim%3Aone'});
  assert.equal(map.selections.length, 1);
  assert.equal(map.selections[0].type, 'explorer:selected');
  assert.equal(map.selections[0].detail.id, 'claim:one');
  assert.equal(map.selections[0].bubbles, true);
  map.search.value = 'Second problem';
  map.search.fire('input');
  map.search.fire('keydown', {key: 'Enter'});
  assert.equal(map.selections.length, 2);
  assert.equal(map.selections[1].detail.id, 'problem:two');
});

test('the explorer carries the view it shows, and a card at the top of its trail goes back to that view by name', async () => {
  // 6 October 2026: the panel is one view at a time (problems, index,
  // filters, how to read) with a kept object over it. The explorer says
  // which view stands, for CSS; the card's way back names the view.
  const map = await mount({explorer: true});
  const explorer = map.canvas.closest('[data-explorer]');
  assert.equal(explorer.getAttribute('data-universe-view'), 'problems', 'at rest the problems stand');
  map.search.value = 'Second problem';
  map.search.fire('input');
  map.search.fire('keydown', {key: 'Enter'});
  assert.equal(explorer.getAttribute('data-universe-view'), 'object', 'a kept object reads over the view');
  assert.match(map.inspector.innerHTML,
    /aria-label="Back to the problems \(Esc\)"><span aria-hidden="true">←<\/span> Problems<\/button>/,
    'the way back says where it goes, never a bare glyph or a vague Close');
  map.document.fire('keydown', {key: 'Escape', target: {tagName: 'BODY'}});
  assert.equal(explorer.getAttribute('data-universe-view'), 'problems', 'Esc returns to the view it came from');
});

test('a search that finds nothing on the map says so, and why, outside the list of matches', async () => {
  const none = element();
  none.hidden = true;
  const map = await mount({explorer: true, extraSelectors: {'[data-universe-none]': none}});
  map.document.activeElement = map.search;
  map.search.value = 'zzqqxx';
  map.search.fire('input');
  assert.equal(none.hidden, false);
  assert.match(none.innerHTML, /Nothing shown on the map matches “zzqqxx”\./);
  assert.match(none.innerHTML, /found once the complete universe is loaded/, 'what is not loaded yet is said, not taken for absence');
  assert.equal(map.results.hidden, true, 'the combobox list stays closed: no option claims a match');
  map.search.value = 'Second';
  map.search.fire('input');
  assert.equal(none.hidden, true);
});
