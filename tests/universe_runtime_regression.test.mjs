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

test('filter feedback counts only connections whose endpoints remain visible', async () => {
  const map = await mount();
  assert.equal(map.count.textContent, '3 objects, 3 of 3 connections drawn');
  map.claims.fire('click');
  assert.equal(map.count.textContent, '2 objects, 1 of 1 connections drawn');
  map.claims.fire('click');
  assert.equal(map.count.textContent, '3 objects, 3 of 3 connections drawn');
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
  assert.equal(map.count.textContent, '100 objects, 2 of 100 connections drawn');
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
  assert.equal(map.count.textContent, '100 objects, 2 of 100 connections drawn');
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
  assert.equal(map.count.textContent, '100 objects, 5 of 100 connections drawn');
  assert.ok(map.hotSegments().every(segment => segment.from.every(Number.isFinite) && segment.to.every(Number.isFinite)));

  map.search.value = 'Fan module 95';
  map.search.fire('input');
  assert.match(map.count.textContent, / · 1 match$/);
  map.search.fire('keydown', {key: 'Enter'});
  assert.equal(map.location.hash, '#o=lean-module%3AFan95');
  assert.match(map.inspector.innerHTML, /Fan module 95/);
  assert.equal(map.hotSegments().length, 1, 'the last module in the complete corpus remains selectable');
  map.search.fire('keydown', {key: 'Escape'});
  assert.equal(map.count.textContent, '100 objects, 3 of 100 connections drawn');

  map.modules.fire('click');
  assert.equal(map.location.hash, '', 'hiding the selected kind clears its pin');
  assert.equal(map.count.textContent, '4 objects, 2 of 2 connections drawn');
  assert.equal(map.hotSegments().length, 0);
  map.modules.fire('click');
  assert.equal(map.count.textContent, '100 objects, 2 of 100 connections drawn');
  map.location.hash = '#o=lean-module%3AFan00';
  map.window.fire('hashchange');
  assert.equal(map.hotSegments().length, 3);
  map.claims.fire('click');
  assert.equal(map.count.textContent, '99 objects, 4 of 99 connections drawn');
  assert.equal(map.hotSegments().length, 2, 'hidden claim removes exactly its incident proof link');
  map.claims.fire('click');
  assert.equal(map.count.textContent, '100 objects, 5 of 100 connections drawn');
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
    assert.equal(map.count.textContent, `32 objects, ${cap} of 31 connections drawn`);
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
  assert.equal(map.count.textContent, '3 objects, 1 of 1 connections drawn · 1 match');
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
  assert.equal(map.count.textContent, '3 objects, 2 of 3 connections drawn');
  map.location.hash = '#o=claim%3Aone';
  map.window.fire('hashchange');
  assert.equal(map.hotSegments().length, 2, 'focusing the claim reveals both incident relationships');
  assert.equal(map.drawnSegments().length, 3);
  assert.equal(map.count.textContent, '3 objects, 3 of 3 connections drawn');
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
    assert.match(map.count.textContent, / · 1 match$/, query);
    map.search.fire('keydown', {key: 'Enter'});
    assert.equal(map.location.hash, '#o=problem%3Aerdos_68');
    assert.match(map.inspector.innerHTML, /The factorial-denominator series/);
    assert.match(map.inspector.innerHTML, /Factorial reciprocal irrationality remains open/);
  }
  for (const query of ['Factorial denominater', 'Denominator factorial', 'erdos 68', 'Erdos68 theorem']) {
    map.search.value = query;
    map.search.fire('input');
    assert.match(map.count.textContent, / · 0 matches$/, query);
    map.search.fire('keydown', {key: 'Enter'});
    assert.equal(map.location.hash, '#o=problem%3Aerdos_68', 'no-match Enter preserves the exact pin');
  }
  map.search.value = 'Erdos68.theorem';
  map.search.fire('input');
  assert.match(map.count.textContent, / · 1 match$/);
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
  assert.match(map.count.textContent, / · 2 matches$/);
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
  assert.match(map.count.textContent, / · 2 matches$/);
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
  assert.match(map.count.textContent, / · 2 matches$/);
  assert.equal(map.location.hash, '#o=problem%3Aerdos_68', 'reconciliation does not repin');
  assert.equal(map.span(), before, 'reconciliation does not reset the camera');
  map.window.fire('popstate');
  map.search.value = 'criterion'; // Same-document traversal restores state after popstate.
  map.flushTimers();
  assert.match(map.count.textContent, / · 1 match$/);
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
  assert.match(map.count.textContent, / · 96 matches$/);
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
  assert.match(map.count.textContent, / · 2 matches$/);
  map.search.value = 'criterion';
  map.search.fire('keydown', {key: 'Enter'}); // Also correct if focus preceded late restoration.
  assert.match(map.count.textContent, / · 1 match$/);
  assert.equal(map.location.hash, '#o=claim%3Afactorial');
  map.search.value = 'Factorial denominater';
  map.search.fire('keydown', {key: 'Enter'});
  assert.match(map.count.textContent, / · 0 matches$/);
  assert.equal(map.location.hash, '#o=claim%3Afactorial', 'no-match Enter retains the pin');
  let stopped = false;
  map.search.fire('keydown', {key: 'Escape', stopPropagation() { stopped = true; }});
  assert.equal(stopped, true, 'search Escape stops the document pin-clear handler');
  assert.equal(map.search.value, '');
  assert.doesNotMatch(map.count.textContent, /matches?$/);
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
