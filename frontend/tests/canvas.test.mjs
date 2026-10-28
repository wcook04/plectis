// Exercise the real renderer with a controlled display clock and DOM geometry.
import test from 'node:test';
import assert from 'node:assert/strict';
import { createMap } from '../src/map/engine.js';
import { build } from '../src/data.js';

function fixture(t, reduced = false, hooks = {}) {
  const saved = new Map();
  let map;
  const install = (key, value) => { saved.set(key, Object.getOwnPropertyDescriptor(globalThis, key)); Object.defineProperty(globalThis, key, { value, writable: true, configurable: true }); };
  t.after(() => { map?.destroy(); for (const [key, descriptor] of saved) if (descriptor) Object.defineProperty(globalThis, key, descriptor); else delete globalThis[key]; });
  const events = () => {
    const listeners = new Map();
    return {
      addEventListener(name, callback) { if (!listeners.has(name)) listeners.set(name, new Set()); listeners.get(name).add(callback); },
      removeEventListener(name, callback) { listeners.get(name)?.delete(callback); },
      emit(name, event = {}) { for (const callback of listeners.get(name) || []) callback(event); },
    };
  };
  let paints = 0, measurements = 0, width = 900, height = 700, fontReady;
  const context = new Proxy({
    clearRect() { paints++; }, measureText(text) { return { width: text.length * 6 }; },
    createRadialGradient() { return { addColorStop() {} }; },
    createLinearGradient() { return { addColorStop() {} }; },
    createPattern() { return {}; },
  }, { get: (target, key) => key in target ? target[key] : () => {} });
  const classes = new Set();
  const chrome = { getBoundingClientRect() { measurements++; return { left: 730, right: 880, top: 10, bottom: 50 }; } };
  const stage = { parentElement: null, querySelectorAll: () => [chrome], classList: {
    contains: (name) => classes.has(name), toggle(name, on) { if (on) classes.add(name); else classes.delete(name); },
  } };
  const canvas = { ...events(), parentElement: stage, style: {}, width: 0, height: 0,
    get clientWidth() { measurements++; return width; }, get clientHeight() { measurements++; return height; },
    getContext: () => context, getBoundingClientRect() { measurements++; return { left: 0, top: 0, right: width, bottom: height }; },
  };
  const motion = { ...events(), matches: reduced };
  const scheme = { ...events(), matches: false };
  const observers = [];
  class Observer { constructor(callback) { this.callback = callback; this.disconnected = false; observers.push(this); } observe() {} unobserve() {} disconnect() { this.disconnected = true; } }
  const fonts = { ...events(), ready: new Promise((resolve) => { fontReady = resolve; }) };
  const document = { ...events(), hidden: false, documentElement: {}, fonts, createElement: () => ({ getContext: () => context }) };
  const window = { ...events(), devicePixelRatio: 1, ResizeObserver: Observer, MutationObserver: Observer, matchMedia: (q) => q.includes('reduced-motion') ? motion : scheme };
  const frames = new Map(); let nextFrame = 1;
  install('window', window); install('document', document); install('ResizeObserver', Observer); install('MutationObserver', Observer);
  install('getComputedStyle', () => ({ getPropertyValue: (name) => name === '--m-ground' ? '#ffffff' : '' }));
  install('requestAnimationFrame', (callback) => { const id = nextFrame++; frames.set(id, callback); return id; });
  install('cancelAnimationFrame', (id) => frames.delete(id));
  const model = build({
    components: [{ organ_id: 'a', title: 'Component A', summary: '', claim_id: 'claim::a', classification: { family: 'formal_math_and_proof', evidence_class: 'semantic_validator' }, formal_subclaim_ids: [], proof_ids: [], receipt_refs: [], wires_to: [], doctrine_ref_ids: ['AX-1'], route_ids: [] }],
    kernels: [], cores: [], coverage: { component_presence: {} },
    explorer: { doctrine: { nodes: [{ id: 'AX-1', kind: 'axiom', title: 'An axiom' }], edges: [] } },
  }, 'revision');
  map = createMap(canvas, model, hooks);
  return { map, canvas, stage, motion, document, window, fonts, fontReady, observers,
    pending: () => frames.size, paints: () => paints, measurements: () => measurements,
    dimensions(w, h) { width = w; height = h; },
    tick(now) { const batch = [...frames]; frames.clear(); for (const [, callback] of batch) callback(now); },
  };
}

test('opening, camera, focus and citation animations paint at most once per display frame and settle', (t) => {
  const f = fixture(t);
  f.map.select('comp:a');
  f.map.emphasise('runtime');
  f.map.showWiring(true);
  for (let now = 0; now <= 4200; now += 16) {
    assert.ok(f.pending() <= 1, 'one browser frame callback, even with concurrent effects');
    const before = f.paints();
    f.tick(now);
    assert.ok(f.paints() - before <= 1, 'one canvas clear/paint per display frame');
  }
  assert.ok(f.paints() > 100, 'animations continue smoothly through the opening');
  assert.equal(f.pending(), 0, 'settled map does not keep a frame loop alive');
  assert.equal(f.map.selectedKey(), 'comp:a');
});

test('stable animation frames reuse geometry; resize, chrome, theme and fonts invalidate it', (t) => {
  const f = fixture(t);
  f.tick(0);
  const before = f.measurements();
  for (let now = 16; now < 200; now += 16) f.tick(now);
  assert.equal(f.measurements(), before, 'drawing does not repeatedly read layout');
  const invalidate = (event) => { const reads = f.measurements(); event(); f.tick(220); assert.ok(f.measurements() > reads); };
  invalidate(() => { f.dimensions(1000, 600); f.observers[0].callback(); });
  assert.equal(f.canvas.width, 1000); assert.equal(f.canvas.height, 600);
  invalidate(() => f.observers[1].callback([{ target: f.stage }]));
  invalidate(() => f.document.emit('plectis:theme'));
  invalidate(() => f.fonts.emit('loadingdone'));
  invalidate(() => f.map.zoomBy(1.2));
});

test('reduced motion settles active effects and disposal cancels frames and observers', async (t) => {
  const f = fixture(t);
  f.map.select('comp:a');
  f.tick(0); f.tick(16);
  f.motion.matches = true; f.motion.emit('change');
  f.tick(32);
  assert.equal(f.pending(), 0, 'turning on reduced motion cancels existing animation loops');
  f.map.setMatches(new Set(['a']));
  assert.equal(f.pending(), 1);
  f.map.destroy();
  assert.equal(f.pending(), 0);
  assert.ok(f.observers.every((observer) => observer.disconnected));
  const before = f.paints();
  f.fontReady(); await Promise.resolve();
  f.window.emit('resize'); f.document.emit('plectis:theme'); f.fonts.emit('loadingdone');
  f.map.resize(); f.map.fit(); f.tick(100);
  assert.equal(f.pending(), 0);
  assert.equal(f.paints(), before, 'late lifecycle callbacks cannot revive a disposed renderer');
});

test('initial reduced motion still draws requested state without an animation loop', (t) => {
  const f = fixture(t, true);
  f.map.select('comp:a'); f.map.showWiring(true); f.map.zoomBy(1.2);
  f.tick(0);
  assert.equal(f.paints(), 1);
  assert.equal(f.pending(), 0);
});

test('choosing never zooms; a preview never moves the camera or restarts the chosen animations', (t) => {
  const told = [];
  const f = fixture(t, false, { skipReveal: true, onHover: (o, info) => told.push([o && o.key, info]) });
  for (let now = 0; now <= 400; now += 16) f.tick(now);
  const before = JSON.stringify(f.map.view());
  f.map.select('rule:AX-1');
  for (let now = 416; now <= 1800; now += 16) f.tick(now);
  assert.equal(f.pending(), 0, 'the choice settles');
  f.map.hoverKey('comp:a');
  assert.equal(told.length, 1, 'a panel row preview is told like a pointer one');
  assert.equal(told[0][0], 'comp:a');
  assert.deepEqual(told[0][1].relation, { kind: 'cites', rule: 'AX-1', component: 'a' });
  assert.equal(told[0][1].source, 'panel');
  f.tick(1816);
  assert.equal(f.pending(), 0, 'a preview over a choice paints once and starts no animation');
  assert.equal(f.map.selectedKey(), 'rule:AX-1');
  assert.equal(f.map.routeState().tracing, 'a', 'the previewed citer is the one traced');
  assert.equal(JSON.stringify(f.map.view()), before);
  f.map.hoverKey(null);
  f.map.hoverKey(null);
  assert.equal(told.length, 2, 'only a change is told');
});

test('gestures paint cached frames, one per display frame, then settle with one crisp full paint', async (t) => {
  const f = fixture(t, false, { skipReveal: true });
  for (let now = 0; now <= 400; now += 16) f.tick(now);
  assert.equal(f.pending(), 0);
  assert.equal(f.map.paintStats().last, 'full');
  const wheel = () => f.canvas.emit('wheel', { deltaY: -40, offsetX: 450, offsetY: 350, ctrlKey: false, preventDefault() {} });
  let now = 416;
  for (let i = 0; i < 4; i += 1) {
    wheel();
    assert.ok(f.pending() <= 1, 'one browser frame callback per display frame');
    const before = f.paints();
    f.tick(now += 16);
    assert.ok(f.paints() - before <= 1, 'one canvas paint per display frame');
    assert.equal(f.map.paintStats().last, 'blit', 'a wheel frame reuses the last crisp frame');
  }
  // A change of choice mid-gesture is always painted in full.
  f.map.select('comp:a');
  f.tick(now += 16);
  assert.equal(f.map.paintStats().last, 'full');
  assert.ok(f.map.paintStats().gesturing);
  await new Promise((resolve) => setTimeout(resolve, 160));
  assert.equal(f.map.paintStats().gesturing, false);
  for (let i = 0; i < 120; i += 1) f.tick(now += 16);
  assert.equal(f.map.paintStats().last, 'full', 'the gesture settles on a crisp full paint');
  assert.equal(f.pending(), 0, 'and then stops asking for frames');
});
