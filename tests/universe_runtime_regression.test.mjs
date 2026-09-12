import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import vm from 'node:vm';

const source = readFileSync(new URL('../../../tools/meta/dissemination/maths_site_assets/universe.js', import.meta.url), 'utf8');

function element(attrs = {}) {
  const events = {};
  const classes = new Set();
  return {
    innerHTML: '', textContent: '', value: '', disabled: false, hidden: false,
    getAttribute: name => attrs[name] ?? null,
    setAttribute: (name, value) => { attrs[name] = value; },
    contains: () => false,
    querySelector: () => null,
    classList: { contains: name => classes.has(name), add: name => classes.add(name),
      remove: name => classes.delete(name), toggle(name, on) { on ? classes.add(name) : classes.delete(name); } },
    addEventListener(name, fn) { (events[name] ||= []).push(fn); },
    fire(name, event = {}) { for (const fn of events[name] || []) fn(event); },
  };
}

async function mount() {
  let arcs = [];
  const context = new Proxy({
    clearRect() { arcs = []; },
    arc(x, y, r) { arcs.push({x, y, r}); },
  }, { get: (target, key) => target[key] ?? (() => {}) });
  const canvas = Object.assign(element({'data-universe-src': 'initial'}), {
    clientWidth: 292, clientHeight: 340, getContext: () => context,
  });
  canvas.classList.add('universe-canvas--page');
  const count = element();
  const inspector = element();
  const search = element();
  const claims = element({'data-universe-lens': 'public_claim', 'aria-pressed': 'true'});
  const zoom = element({'data-universe-zoom': 'out'});
  const full = element({'data-graph-src': 'graph', 'data-layout-src': 'layout'});
  const stage = Object.assign(element(), {
    querySelector: s => s === 'canvas' ? canvas : null,
    querySelectorAll: s => s === '[data-universe-zoom]' ? [zoom] : [],
  });
  const selectors = {'[data-universe-inspector]': inspector, '[data-universe-count]': count,
    '[data-universe-search]': search, '[data-universe-load-full]': full};
  const document = Object.assign(element(), {
    readyState: 'complete', documentElement: element(), activeElement: null,
    querySelector: s => selectors[s] || null,
    querySelectorAll: s => s === '[data-universe-stage]' ? [stage] : s === '[data-universe-lens]' ? [claims] : [],
  });
  const location = {pathname: '/maths/universe.html', search: '', hash: ''};
  const window = Object.assign(element(), {
    location, devicePixelRatio: 1, isSecureContext: false,
    history: {replaceState(_a, _b, url) { location.hash = new URL(url, 'http://test').hash; }},
  });
  const nodes = [
    {id: 'problem:one', kind: 'problem', label: 'First problem', x: -500, y: 0},
    {id: 'problem:two', kind: 'problem', label: 'Second problem', x: 500, y: 0},
    {id: 'claim:one', kind: 'public_claim', label: 'One checked claim', x: 0, y: 100},
  ];
  const module = {id: 'lean-module:Deep', kind: 'lean_module', label: 'Deep module'};
  const requests = [];
  const data = {
    initial: {nodes, edges: [[0, 2], [1, 2], [0, 1]]},
    graph: {nodes: [...nodes, module], edges: [{source: module.id, target: nodes[0].id}]},
    layout: {positions: Object.fromEntries([...nodes, {...module, x: 0, y: 200}].map(n => [n.id, [n.x, n.y]]))},
  };
  vm.runInNewContext(source, {document, window, navigator: {},
    getComputedStyle: () => ({getPropertyValue: () => ''}),
    fetch: async url => { requests.push(url); return {json: async () => data[url]}; },
    setTimeout: fn => { fn(); return 1; }, clearTimeout() {},
  });
  const settle = () => new Promise(resolve => setImmediate(resolve));
  await settle();
  return {canvas, count, inspector, search, claims, zoom, full, location, window,
    requests, settle, arcs: () => arcs,
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
  assert.equal(map.count.textContent, '3 objects, 3 connections shown');
  map.claims.fire('click');
  assert.equal(map.count.textContent, '2 objects, 1 connections shown');
  map.claims.fire('click');
  assert.equal(map.count.textContent, '3 objects, 3 connections shown');
});

test('resizing preserves an explored scale instead of refitting the graph', async () => {
  const map = await mount();
  map.zoom.fire('click');
  const before = map.span();
  map.canvas.clientWidth = 500;
  map.window.fire('resize');
  assert.ok(Math.abs(map.span() - before) < 1e-9);
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
