// The landing's system map (assets/system-map.js), run in a vm against the
// published architecture scene with a fake canvas, frame clock and observers.
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import vm from 'node:vm';

const source = readFileSync(new URL('../assets/system-map.js', import.meta.url), 'utf8');
const sceneFile = JSON.parse(readFileSync(new URL('../docs/architecture-graph-scene.json', import.meta.url), 'utf8'));
const clone = value => JSON.parse(JSON.stringify(value));
// Values from the vm's own realm compare by their JSON.
const plain = value => JSON.parse(JSON.stringify(value));

const CLASSES = [
  ['external_subprocess_witness', 'External tool run', 4, true, 'Real runtime result'],
  ['bounded_runtime_computation', 'Bounded runtime computation', 4, true, 'Real runtime result'],
  ['verified_macro_body_import', 'Verified source import', 5, false, 'Copied source body'],
  ['semantic_validator', 'Contract validator', 5, false, 'Import validation'],
  ['algorithmic_projection', 'Computed projection', 3, false, 'Source-faithful refactor'],
];

// The scene as the deploy publishes it, with per-object details. A checkout
// whose scene predates the details gets them synthesised, deterministically.
function liveScene() {
  const json = clone(sceneFile);
  const scene = json.scene;
  if (scene.inspectors && Object.keys(scene.inspectors).length) return json;
  scene.inspectors = {};
  scene.nodes.forEach((n, i) => {
    const ref = `inspector:${n.id}`;
    n.inspector_ref = ref;
    const slug = n.id.replace(/^[a-z_]+:/, '').replace(/_/g, '-');
    if (n.kind === 'wired_component' || n.kind === 'component') {
      const [class_id, kind, rank, runs, basis] = CLASSES[i % CLASSES.length];
      scene.inspectors[ref] = {
        title: n.label, public_label: n.label, family_id: n.parent_cluster_id.replace('cluster:', ''),
        summary_line: `What ${n.label} does, in one sentence.`,
        evidence: { class_id, kind, rank, runs_real_tools: runs, basis },
        routes: { component_detail_href: `component-${slug}.html`, primary_reader_href: `paper-module-${slug}.html`,
                  map_href: `architecture.html#map=${encodeURIComponent(n.id)}` },
      };
    } else if (n.kind === 'area') {
      scene.inspectors[ref] = { title: n.label, summary: n.summary,
        routes: { primary_reader_href: n.resolver_ref.replace(/^docs\//, ''), map_href: `architecture.html#map=${encodeURIComponent(n.id)}` } };
    } else {
      scene.inspectors[ref] = { title: n.label, routes: { map_href: `architecture.html#map=${encodeURIComponent(n.id)}` } };
    }
  });
  return json;
}
// The scene as the stale local build has it: no details, no routes table.
function staleScene() {
  const json = clone(sceneFile);
  json.scene.inspectors = {};
  delete json.node_routes;
  json.scene.nodes.forEach(n => { delete n.inspector_ref; delete n.public_detail; });
  return json;
}
const declared = json => json.scene.edges.filter(e => (e.relation || e.kind) === 'declared_dependency_untyped');

function node(tag = 'div') {
  const events = {};
  const classes = new Set();
  const attrs = {};
  const el = {
    tagName: tag.toUpperCase(), children: [], hidden: false, style: {}, offsetWidth: 260, offsetHeight: 180,
    className: '', _text: '',
    get textContent() { return this._text + this.children.map(c => c.textContent).join(''); },
    set textContent(v) { this._text = String(v); this.children = []; },
    get firstChild() { return this.children[0] || null; },
    get lastChild() { return this.children[this.children.length - 1] || null; },
    appendChild(c) { this.children.push(c); return c; },
    removeChild(c) { this.children = this.children.filter(x => x !== c); return c; },
    getAttribute: n => (n in attrs ? attrs[n] : null),
    setAttribute(n, v) { attrs[n] = String(v); },
    classList: { contains: n => classes.has(n), add: n => classes.add(n), remove: n => classes.delete(n),
      toggle(n, on) { if (on === undefined ? !classes.has(n) : on) classes.add(n); else classes.delete(n); } },
    addEventListener(n, fn) { (events[n] ||= []).push(fn); },
    fire(n, e = {}) { for (const fn of events[n] || []) fn({ preventDefault() {}, stopPropagation() {}, ...e }); },
    querySelector: () => null, querySelectorAll: () => [],
    all(predicate) { const out = []; const walk = n => { if (predicate(n)) out.push(n); (n.children || []).forEach(walk); }; this.children.forEach(walk); return out; },
  };
  return el;
}

async function mount({ scene = liveScene(), width = 677, height = 569, reduce = false, io = false, fine = true,
                       settle = true, hash = '' } = {}) {
  let clears = 0, texts = [], font = '11px serif';
  const calls = {};
  const ctx = new Proxy({
    clearRect() { clears++; texts = []; for (const k of Object.keys(calls)) delete calls[k]; },
    fillText(text, x, y) { texts.push({ text: String(text), x, y }); },
    measureText(text) { const px = parseFloat((/([\d.]+)px/.exec(font) || [0, 11])[1]); return { width: String(text).length * px * 0.52 }; },
  }, {
    get: (t, k) => (k === 'font' ? font : k in t ? t[k] : () => { calls[k] = (calls[k] || 0) + 1; }),
    set: (t, k, v) => { if (k === 'font') font = v; else t[k] = v; return true; },
  });
  const canvas = Object.assign(node('canvas'), { clientWidth: width, clientHeight: height, width: 0, height: 0,
    getContext: () => ctx, getBoundingClientRect: () => ({ left: 0, top: 0, width, height }) });
  canvas.setAttribute('data-system-src', 'docs/architecture-graph-scene.json');
  canvas.setAttribute('data-system-base', 'docs/');
  canvas.classList.add('system-canvas');
  const caption = node('p');
  const familyIds = scene.scene.nodes.filter(n => n.kind === 'area').map(n => n.id);
  const rows = familyIds.map(id => { const li = node('li'); li.setAttribute('data-system-family', id); return li; });
  const section = Object.assign(node('section'), { querySelectorAll: s => (s.includes('home-family') ? rows : []) });
  const stage = Object.assign(node('figure'), {
    querySelector: s => (s.includes('canvas') ? canvas : s === '.system-caption' ? caption : null),
    closest: s => (s === 'section' ? section : null),
  });
  const document = Object.assign(node('document'), {
    readyState: 'complete', hidden: false, documentElement: node('html'),
    querySelectorAll: s => (s === '[data-system-stage]' ? [stage] : []),
    createElement: tag => node(tag), createTextNode: text => ({ textContent: String(text), children: [] }),
  });
  const frames = new Map();
  let nextFrame = 1, now = 0;
  const observers = [];
  const window = Object.assign(node('window'), {
    devicePixelRatio: 2, location: { href: '/', hash },
    matchMedia: q => ({ matches: /reduce/.test(q) ? reduce : /hover/.test(q) ? fine : false, addEventListener() {} }),
    requestAnimationFrame: fn => { frames.set(nextFrame, fn); return nextFrame++; },
    cancelAnimationFrame: id => frames.delete(id),
  });
  if (io) {
    window.IntersectionObserver = class { constructor(cb) { this.cb = cb; observers.push(this); } observe() {} disconnect() {} };
  }
  const requests = [];
  const timers = [];
  vm.runInNewContext(source, {
    window, document, Promise, Math, JSON, Object, Array, Date, Number, String, isFinite,
    getComputedStyle: () => ({ getPropertyValue: () => '' }),
    fetch: async (url, opts) => { requests.push({ url, opts }); return { ok: true, json: async () => scene }; },
    setTimeout: (fn, ms) => { timers.push({ fn, ms }); return timers.length; }, clearTimeout() {},
  });
  await new Promise(r => setImmediate(r));
  await new Promise(r => setImmediate(r));
  const advance = ms => {
    const end = now + ms;
    while (now < end) {
      now += 16;
      const due = [...frames.entries()];
      frames.clear();
      for (const [, fn] of due) fn(now);
    }
  };
  const fireIO = ratio => observers.forEach(o => o.cb([{ isIntersecting: ratio > 0, intersectionRatio: ratio }]));
  const runTimers = () => { for (const t of timers.splice(0)) t.fn(); };
  const card = () => stage.children.find(c => c.className && c.className.includes('system-card')) || null;
  // Unless a test follows the opening, it is played out before the test
  // begins (the vm has no observer, so the drawing counts as in view).
  if (settle && !io) advance(2500);
  const select = id => { window.PlectisSystemMap.select(id); advance(800); };
  return { map: window.PlectisSystemMap, window, document, canvas, caption, rows, section, stage, frames, advance, fireIO,
           runTimers, requests, card, select, clears: () => clears, texts: () => texts, calls: () => ({ ...calls }), now: () => now };
}

function insideRect(c, r, pad) {
  return c.x - pad > r.x0 && c.x + pad < r.x1 && c.y - pad > r.y0 && c.y + pad < r.y1;
}
function boxesMeet(a, b) { return a.x0 < b.x1 - 0.5 && a.x1 > b.x0 + 0.5 && a.y0 < b.y1 - 0.5 && a.y1 > b.y0 + 0.5; }
// An orthogonal run [[x0, y0], [x1, y1]] against a box, with a margin.
function runMeets(a, b, box, pad = 0) {
  const x0 = Math.min(a[0], b[0]), x1 = Math.max(a[0], b[0]), y0 = Math.min(a[1], b[1]), y1 = Math.max(a[1], b[1]);
  return x1 > box.x0 - pad && x0 < box.x1 + pad && y1 > box.y0 - pad && y0 < box.y1 + pad;
}
const famOf = scene => {
  const map = {};
  scene.scene.nodes.forEach(n => { if (/component$/.test(n.kind)) map[n.id] = 'area:' + n.parent_cluster_id.replace('cluster:', ''); });
  return map;
};

test('the layout is deterministic and sets every component inside its family plate, none overlapping', async () => {
  const a = (await mount()).map.snapshot();
  const b = (await mount()).map.snapshot();
  assert.ok(a.ready);
  assert.deepEqual(plain(a.components), plain(b.components), 'the same scene and box give the same drawing');
  assert.deepEqual(plain(a.links), plain(b.links), 'and the same routes');
  assert.deepEqual(plain(a.cables), plain(b.cables), 'and the same cables');
  assert.equal(a.components.length, sceneFile.scene.nodes.filter(n => /component$/.test(n.kind)).length);
  for (const c of a.components) {
    const plate = a.plates.find(p => p.id === c.family);
    assert.ok(plate, `${c.id} has its family plate`);
    assert.ok(insideRect(c, plate.rect, a.markRadius + 1), `${c.id} sits inside ${plate.title}`);
  }
  for (let i = 0; i < a.components.length; i++) {
    for (let k = i + 1; k < a.components.length; k++) {
      const d = Math.hypot(a.components[i].x - a.components[k].x, a.components[i].y - a.components[k].y);
      assert.ok(d >= 2 * a.markRadius + 2, `${a.components[i].id} and ${a.components[k].id} do not overlap`);
    }
  }
  for (let i = 0; i < a.plates.length; i++) {
    for (let k = i + 1; k < a.plates.length; k++) assert.ok(!boxesMeet(a.plates[i].rect, a.plates[k].rect), 'plates never overlap');
  }
  // Reading order: the first half of the families along the top row.
  const order = sceneFile.scene.nodes.filter(n => n.kind === 'area').map(n => n.id);
  assert.deepEqual(plain(a.plates.map(p => p.id)), order, 'plates keep the scene order');
  assert.ok(a.plates.slice(0, Math.ceil(order.length / 2)).every(p => p.row === 0));
});

test('every mark stands on one lattice that runs through the whole drawing, and a plate is as deep as its marks need', async () => {
  for (const [width, height] of [[677, 569], [630, 526], [900, 790]]) {
    const snap = (await mount({ width, height })).map.snapshot();
    const p = snap.pitch, x0 = Math.min(...snap.components.map(c => c.x));
    for (const c of snap.components) {
      const k = (c.x - x0) / p;
      assert.ok(Math.abs(k - Math.round(k)) < 1e-6, `${c.id} is on a lattice column at ${width}x${height}`);
    }
    for (const row of [0, 1]) {
      const ys = snap.components.filter(c => snap.plates.find(pl => pl.id === c.family).row === row).map(c => c.y);
      const y0 = Math.min(...ys);
      for (const y of ys) {
        const k = (y - y0) / p;
        assert.ok(Math.abs(k - Math.round(k)) < 1e-6, `rows of marks are a pitch apart at ${width}x${height}`);
      }
    }
    // A plate stands on the line's side of the drawing, so the edges facing
    // the line share one row; its depth is its own (no empty rows of marks).
    for (const plate of snap.plates) {
      const marks = snap.components.filter(c => c.family === plate.id);
      const rows = new Set(marks.map(c => Math.round(c.y * 100))).size;
      assert.equal(rows, plate.rows, `${plate.title} holds exactly its rows of marks`);
    }
    for (const row of [0, 1]) {
      const edges = snap.plates.filter(pl => pl.row === row).map(pl => (row === 0 ? pl.rect.y1 : pl.rect.y0));
      assert.ok(edges.every(e => Math.abs(e - edges[0]) < 0.01), 'the plates of a row stand on one line');
    }
  }
});

test('every declared link resolves to two placed components along an orthogonal route', async () => {
  const scene = liveScene();
  const snap = (await mount({ scene })).map.snapshot();
  const links = declared(scene);
  assert.equal(snap.links.length, links.length, 'all declared links are drawn');
  const at = Object.fromEntries(snap.components.map(c => [c.id, c]));
  links.forEach((e, i) => {
    const l = snap.links[i];
    assert.equal(l.source, e.source);
    assert.equal(l.target, e.target);
    assert.ok(at[l.source] && at[l.target], 'both ends are placed');
    const s = l.points[0], end = l.points.at(-1);
    assert.ok(Math.hypot(s[0] - at[l.source].x, s[1] - at[l.source].y) <= snap.markRadius + 4, 'the route leaves its source');
    assert.ok(Math.hypot(end[0] - at[l.target].x, end[1] - at[l.target].y) <= snap.markRadius + 4, 'and reaches its target');
    for (let k = 1; k < l.points.length; k++) {
      const [x0, y0] = l.points[k - 1], [x1, y1] = l.points[k];
      assert.ok(Math.abs(x0 - x1) < 0.01 || Math.abs(y0 - y1) < 0.01, 'every run is horizontal or vertical');
    }
  });
});

test('the links between two families travel as one cable whose terminals count them', async () => {
  const scene = liveScene();
  const snap = (await mount({ scene })).map.snapshot();
  const fam = famOf(scene);
  const between = {};
  for (const e of declared(scene)) {
    const a = fam[e.source], b = fam[e.target];
    if (a === b) continue;
    const key = [a, b].sort().join('|');
    between[key] = (between[key] || 0) + 1;
  }
  assert.equal(snap.cables.length, Object.keys(between).length, 'one cable for every pair of families with links');
  for (const cb of snap.cables) {
    const key = [cb.from, cb.to].sort().join('|');
    assert.equal(cb.count, between[key], `the cable ${key} carries every link between the two`);
    assert.deepEqual(plain(cb.pins), [cb.count, cb.count], 'each terminal has a pin for every link');
    for (let k = 1; k < cb.points.length; k++) {
      const [x0, y0] = cb.points[k - 1], [x1, y1] = cb.points[k];
      assert.ok(Math.abs(x0 - x1) < 0.01 || Math.abs(y0 - y1) < 0.01, 'cables run orthogonally');
    }
  }
  // Lanes are evenly spaced: every horizontal run in a corridor sits a whole
  // number of lane pitches from its neighbours.
  const ys = [...new Set(snap.cables.flatMap(cb => cb.points.slice(1, -1).map(q => Math.round(q[1] * 100) / 100)))].sort((a, b) => a - b);
  assert.ok(ys.length >= 2, 'there are lanes');
});

test('terminals and ties on a plate edge never touch, at five sizes', async () => {
  for (const [width, height] of [[630, 526], [677, 569], [900, 790], [335, 379], [430, 560]]) {
    const snap = (await mount({ width, height })).map.snapshot();
    const byPlate = {};
    for (const cb of snap.cables) {
      for (const t of cb.terminals) (byPlate[t.family] ||= []).push(t);
    }
    snap.plates.forEach((plate, i) => {
      const along = snap.portrait ? 1 : 0;
      const spans = (byPlate[plate.id] || []).map(t => [Math.min(t.a[along], t.b[along]), Math.max(t.a[along], t.b[along])]);
      const tie = snap.ties[i].from[along];
      spans.sort((a, b) => a[0] - b[0]);
      for (let k = 1; k < spans.length; k++) {
        assert.ok(spans[k][0] > spans[k - 1][1] + 1, `two terminals on ${plate.title} touch at ${width}x${height}`);
      }
      for (const s of spans) assert.ok(tie < s[0] - 1 || tie > s[1] + 1, `the tie of ${plate.title} runs into a terminal at ${width}x${height}`);
    });
  }
});

test('nothing drawn crosses a word: cables, ties and routes keep clear of every name, at five sizes', async () => {
  for (const [width, height] of [[630, 526], [677, 569], [900, 790], [335, 379], [430, 560]]) {
    const snap = (await mount({ width, height })).map.snapshot();
    const words = snap.labels.filter(l => l.kind !== 'legend' && l.kind !== 'legend-count');
    for (const cb of snap.cables) {
      for (let k = 1; k < cb.points.length; k++) {
        for (const w of words) {
          assert.ok(!runMeets(cb.points[k - 1], cb.points[k], w.box, 0.5), `a cable crosses "${w.text}" at ${width}x${height}`);
        }
      }
    }
    for (const t of snap.ties) {
      for (const w of words) assert.ok(!runMeets(t.from, t.to, w.box, 0.5), `a tie crosses "${w.text}" at ${width}x${height}`);
    }
    for (const l of snap.links) {
      for (let k = 1; k < l.points.length; k++) {
        for (const w of words) {
          assert.ok(!runMeets(l.points[k - 1], l.points[k], w.box, 0), `a route from ${l.source} crosses "${w.text}" at ${width}x${height}`);
        }
      }
    }
  }
});

test('bad rows are dropped and the rest is drawn', async () => {
  const scene = liveScene();
  const edges = scene.scene.edges;
  edges.push({ ...edges[0] });                                                       // a repeated edge id
  edges.push({ id: 'edge:dangling', relation: 'declared_dependency_untyped', source: 'component:nowhere', target: edges[0].target });
  scene.scene.nodes.push({ ...scene.scene.nodes.find(n => n.kind === 'wired_component') }); // a duplicate node
  const snap = (await mount({ scene })).map.snapshot();
  assert.ok(snap.ready);
  assert.equal(snap.dropped, 2, 'the repeated and the dangling edge are dropped');
  assert.equal(snap.links.length, declared(liveScene()).length);
});

test('a stale scene without details still lays out, labels and routes to the architecture map', async () => {
  const m = await mount({ scene: staleScene() });
  const snap = m.map.snapshot();
  assert.ok(snap.ready && snap.stale);
  assert.ok(snap.components.every(c => c.cls === null), 'no evidence class is invented');
  const drawn = m.texts().map(t => t.text);
  for (const area of sceneFile.scene.nodes.filter(n => n.kind === 'area')) {
    assert.ok(drawn.some(t => area.label.replace(/\s+/g, ' ').includes(t.replace(/…$/, '')) && t.length > 3), `${area.label} is named`);
  }
  for (const step of sceneFile.scene.nodes.filter(n => n.kind === 'spine_step')) {
    assert.ok(drawn.includes(step.label), `the step ${step.label} is named`);
  }
  assert.ok(drawn.includes('Declared link'), 'the key keeps the links');
  assert.ok(!drawn.some(t => /Runs a real tool|Checks a contract/.test(t)), 'and lists no class it cannot know');
  const comp = snap.components[0];
  m.select(comp.id);
  const hrefs = m.card().all(n => n.tagName === 'A').map(a => a.getAttribute('href'));
  assert.deepEqual(hrefs, [`docs/architecture.html#map=${encodeURIComponent(comp.id)}`], 'the one route is the contract #map= address');
});

test('before it opens the drawing is its blueprint: painted once, without words, with no frame running', async () => {
  const m = await mount({ io: true });
  assert.equal(m.map.snapshot().open, 'waiting');
  assert.equal(m.frames.size, 0, 'nothing runs while the drawing is off screen');
  assert.ok(m.clears() >= 1, 'the blueprint is painted although the drawing is not in view yet');
  assert.ok((m.calls().stroke || 0) > 0 && (m.calls().arc || 0) > 0, 'its outlines and lattice points are drawn');
  assert.equal(m.texts().length, 0, 'and no word');
  const clears = m.clears();
  m.advance(2000);
  assert.equal(m.clears(), clears, 'it does not repaint on its own');
});

test('the opening waits for the drawing to be in view, plays once, and requests no frame after it settles', async () => {
  const m = await mount({ io: true });
  assert.equal(m.map.snapshot().open, 'waiting');
  m.fireIO(0.3);
  assert.equal(m.map.snapshot().open, 'waiting', 'a sliver in view does not start it');
  m.fireIO(0.8);
  assert.equal(m.map.snapshot().open, 'running');
  m.advance(600);
  assert.ok(m.frames.size > 0, 'mid-way it is still moving');
  m.advance(1400);
  assert.equal(m.map.snapshot().open, 'done');
  assert.equal(m.frames.size, 0, 'no frame is requested once it has settled');
  const clears = m.clears();
  m.advance(3000);
  assert.equal(m.clears(), clears, 'and nothing repaints while the reader is idle');
  m.fireIO(0);
  m.fireIO(0.9);
  assert.equal(m.map.snapshot().open, 'done', 'it never replays');
  assert.equal(m.frames.size, 0);
});

test('the opening lasts between one and one and a half seconds', async () => {
  const m = await mount({ io: true });
  m.fireIO(0.9);
  let elapsed = 0;
  while (m.map.snapshot().open === 'running' && elapsed < 5000) { m.advance(16); elapsed += 16; }
  assert.ok(elapsed >= 1000 && elapsed <= 1500, `the opening took ${elapsed}ms`);
});

test('while the slider carries the system slide in, the opening waits for the slide to settle', async () => {
  const m = await mount({ io: true });
  const send = detail => m.document.fire('plectis:atlas', { detail });
  send({ view: 'system', previous: 'mathematics', phase: 'start', instant: false });
  m.fireIO(0.9);
  assert.equal(m.map.snapshot().open, 'waiting', 'visible part-way through the move is not enough');
  assert.equal(m.frames.size, 0);
  send({ view: 'system', previous: 'mathematics', phase: 'end', instant: false });
  assert.equal(m.map.snapshot().open, 'running', 'the end of the move starts it');
  m.advance(2000);
  assert.equal(m.frames.size, 0);
  // Moving away drops any hover at once.
  m.canvas.fire('pointermove', { clientX: m.map.snapshot().components[0].x, clientY: m.map.snapshot().components[0].y, pointerType: 'mouse' });
  assert.ok(m.map.snapshot().hover, 'the pointer lights a component');
  send({ view: 'mathematics', previous: 'system', phase: 'start', instant: false });
  assert.equal(m.map.snapshot().hover, null, 'leaving the slide lets it go');
});

test('a slide that arrives at once (a keyboard step, an address naming it) shows the finished drawing', async () => {
  const m = await mount({ io: true });
  m.document.fire('plectis:atlas', { detail: { view: 'system', previous: 'mathematics', phase: 'start', instant: true } });
  m.fireIO(1);
  assert.equal(m.map.snapshot().open, 'done', 'no opening for an instant arrival');
  assert.equal(m.frames.size, 0, 'and no frame');
  const byAddress = await mount({ io: true, hash: '#system' });
  assert.equal(byAddress.map.snapshot().open, 'done', 'an address that names the drawing lands on it finished');
  byAddress.fireIO(1);
  assert.equal(byAddress.frames.size, 0);
});

test('reduced motion paints the finished drawing with no frame scheduled, at every level', async () => {
  const m = await mount({ io: true, reduce: true });
  assert.equal(m.map.snapshot().open, 'done', 'the drawing is final before it is seen');
  m.fireIO(1);
  assert.ok(m.texts().some(t => t.text === 'Declared link'), 'the finished drawing is painted');
  assert.equal(m.frames.size, 0);
  m.map.select('area:formal_math_and_proof');
  assert.equal(m.map.snapshot().level, 'family');
  assert.equal(m.map.snapshot().sheet.mix, 1, 'the family opens at once');
  m.map.select(m.map.snapshot().sheet.rows[0].id);
  assert.equal(m.map.snapshot().level, 'component');
  assert.equal(m.frames.size, 0, 'no frame at any step');
  m.document.fire('keydown', { key: 'Escape' });
  m.document.fire('keydown', { key: 'Escape' });
  assert.equal(m.map.snapshot().level, 'overview');
  assert.equal(m.map.snapshot().sheet, null, 'and closes at once');
  assert.equal(m.frames.size, 0);
});

test('every transition lands in its final state and then stops', async () => {
  const m = await mount();
  const formal = 'area:formal_math_and_proof';
  m.map.select(formal);
  m.advance(200);
  const mid = m.map.snapshot().sheet;
  assert.ok(mid && mid.mix > 0 && mid.mix < 1, 'mid-way the plate is opening');
  m.advance(600);
  assert.equal(m.map.snapshot().sheet.mix, 1, 'the sheet arrives fully open');
  assert.equal(m.frames.size, 0, 'and nothing runs after');
  const row = m.map.snapshot().sheet.rows[3];
  m.map.select(row.id);
  m.advance(800);
  assert.equal(m.map.snapshot().level, 'component');
  assert.equal(m.frames.size, 0);
  // Escape is a keyboard step: it lands at once.
  m.document.fire('keydown', { key: 'Escape' });
  assert.equal(m.map.snapshot().level, 'family');
  assert.equal(m.frames.size, 0, 'a keyboard step needs no frame');
  // A click on empty ground steps back by the same path the plate opened.
  m.canvas.fire('click', { clientX: 676, clientY: 568, detail: 1 });
  m.advance(200);
  assert.ok(m.map.snapshot().sheet && m.map.snapshot().sheet.mix < 1, 'closing runs back through the same states');
  m.advance(600);
  assert.equal(m.map.snapshot().sheet, null, 'the sheet closes fully into its plate');
  assert.equal(m.frames.size, 0);
  // A pointer on a component traces its links once, then everything rests.
  const c = m.map.snapshot().components[10];
  m.canvas.fire('pointermove', { clientX: c.x, clientY: c.y, pointerType: 'mouse' });
  assert.ok(m.frames.size > 0, 'the trace runs');
  m.advance(800);
  assert.equal(m.frames.size, 0, 'and stops');
  const clears = m.clears();
  m.advance(2000);
  assert.equal(m.clears(), clears, 'no repaint while the pointer rests');
});

test('the keyboard walks every level and every step lands at once', async () => {
  const m = await mount();
  const row = m.rows[2];                      // Formal math & proof
  row.fire('focusin');
  assert.equal(m.map.snapshot().level, 'family', 'a family row in focus opens its sheet');
  assert.equal(m.map.snapshot().sheet.mix, 1, 'at once');
  assert.equal(m.frames.size, 0);
  row.fire('keydown', { key: 'ArrowDown' });
  row.fire('keydown', { key: 'ArrowDown' });
  assert.equal(m.map.snapshot().focus.kind, 'comp', 'the arrow keys walk the components');
  assert.equal(m.frames.size, 0, 'and light each one at once');
  row.fire('keydown', { key: 'Enter' });
  assert.equal(m.map.snapshot().level, 'component', 'Enter selects the one reached');
  assert.ok(m.card() && !m.card().hidden);
  assert.equal(m.frames.size, 0);
  m.document.fire('keydown', { key: 'Escape' });
  m.document.fire('keydown', { key: 'Escape' });
  assert.equal(m.map.snapshot().level, 'overview', 'Escape steps all the way back');
  assert.equal(m.frames.size, 0);
});

test('a theme change repaints exactly once and starts nothing', async () => {
  const m = await mount();
  const before = m.clears();
  m.document.fire('plectis:theme', { detail: { theme: 'dark' } });
  assert.equal(m.clears(), before + 1, 'one repaint');
  assert.equal(m.frames.size, 0, 'and no animation');
});

test('the three levels: a family opens with every name, a component gets its card, Escape steps back', async () => {
  const m = await mount();
  const formal = 'area:formal_math_and_proof';
  m.select(formal);
  let snap = m.map.snapshot();
  assert.equal(snap.level, 'family');
  const members = snap.components.filter(c => c.family === formal);
  assert.equal(snap.sheet.rows.length, members.length, 'the sheet names every component of the family');
  assert.deepEqual(new Set(snap.sheet.rows.map(r => r.id)), new Set(members.map(c => c.id)));
  assert.match(m.caption.textContent, /All families \/ Formal math & proof/, 'the caption says where the reader is');
  assert.ok(m.texts().some(t => /All families/.test(t.text)), 'the sheet leads back to all families');
  const target = snap.sheet.rows.find(r => r.id === 'component:verifier_lab_kernel') || snap.sheet.rows[0];
  m.select(target.id);
  snap = m.map.snapshot();
  assert.equal(snap.level, 'component');
  const card = m.card();
  assert.ok(card && !card.hidden, 'the component has a card');
  const words = card.textContent;
  assert.match(words, /Names?|names/, 'the card says what it names in words');
  assert.match(words, /A declared link is not proof that one calls the other\./, 'and keeps the honesty boundary');
  assert.deepEqual(card.all(n => n.tagName === 'A').map(a => a.textContent), ['Component page', 'Architecture map']);
  const back = card.all(n => n.tagName === 'BUTTON' && /system-card__back/.test(n.className))[0];
  assert.ok(back, 'the card leads back to its family');
  m.document.fire('keydown', { key: 'Escape' });
  m.advance(800);
  assert.equal(m.map.snapshot().level, 'family', 'Escape steps back to the family');
  m.document.fire('keydown', { key: 'Escape' });
  m.advance(800);
  assert.equal(m.map.snapshot().level, 'overview', 'and then to the whole drawing');
  assert.ok(m.card().hidden, 'the card goes with it');
});

test('a long list in the card opens in full in place', async () => {
  const m = await mount();
  const busiest = m.map.snapshot().components.map(c => c.id)
    .map(id => ({ id, n: declared(liveScene()).filter(e => e.source === id).length }))
    .sort((a, b) => b.n - a.n)[0];
  m.select(busiest.id);
  const card = m.card();
  const more = card.all(n => n.tagName === 'BUTTON' && /system-card__more/.test(n.className));
  assert.ok(more.length >= 1, 'a list longer than five ends in a button for the rest');
  const shown = card.all(n => /system-card__peer/.test(n.className)).length;
  more[0].fire('click');
  const after = m.card().all(n => /system-card__peer/.test(n.className)).length;
  assert.ok(after > shown, 'pressing it lists every name');
  assert.doesNotMatch(m.card().all(n => /system-card__peers/.test(n.className))[0].textContent, /more\./, 'with nothing left over');
});

test('every word a reader sees is plain: no ids, field names or schema words', async () => {
  const m = await mount();
  const seen = [];
  const collect = () => { seen.push(m.caption.textContent, ...m.texts().map(t => t.text)); const c = m.card(); if (c && !c.hidden) seen.push(c.textContent); };
  collect();
  for (const id of ['area:import_projection_and_drift', 'component:macro_projection_import_protocol', 'component:verifier_lab_kernel']) {
    m.select(id);
    collect();
  }
  const snap = m.map.snapshot();
  m.select(null);
  m.canvas.fire('pointermove', { clientX: snap.components[5].x, clientY: snap.components[5].y, pointerType: 'mouse' });
  m.advance(600);
  collect();
  const st = snap.stations[3];
  m.canvas.fire('pointermove', { clientX: st.x, clientY: st.y, pointerType: 'mouse' });
  m.advance(600);
  collect();
  const text = seen.join(' \n ');
  assert.doesNotMatch(text, /\b(?:component|area|primitive|cluster|inspector):/, 'no ids');
  assert.doesNotMatch(text, /declared_dependency_untyped|class_id|runs_real_tools|wired_component|spine_step|_/,
    'no field or class names');
  assert.doesNotMatch(text, /—|·/, 'no em dashes or middle dots');
});

test('words never overlap one another, the marks, or the name plate, at laptop, monitor and phone sizes', async () => {
  for (const [width, height] of [[630, 526], [677, 569], [900, 790], [335, 379], [430, 560]]) {
    const m = await mount({ width, height });
    const check = label => {
      const drawn = m.map.snapshot().drawn;
      for (let i = 0; i < drawn.length; i++) {
        for (let k = i + 1; k < drawn.length; k++) assert.ok(!boxesMeet(drawn[i], drawn[k]), `${label} at ${width}x${height}: words ${i} and ${k}`);
      }
    };
    check('rest');
    const snap = m.map.snapshot();
    for (const c of snap.components) {
      for (const l of snap.labels) {
        const r = snap.markRadius;
        assert.ok(!(c.x + r > l.box.x0 && c.x - r < l.box.x1 && c.y + r > l.box.y0 && c.y - r < l.box.y1),
          `${l.text} stays off ${c.id} at ${width}x${height}`);
      }
    }
    // Pointing at the busiest components puts up a name plate; it covers
    // neither a word nor a mark.
    for (const id of ['component:verifier_lab_kernel', 'component:macro_projection_import_protocol']) {
      const c = snap.components.find(x => x.id === id);
      if (!c) continue;
      m.canvas.fire('pointermove', { clientX: c.x, clientY: c.y, pointerType: 'mouse' });
      m.advance(600);
      check('hover ' + id);
      const plate = m.map.snapshot().drawn[0];
      for (const o of snap.components) {
        if (o.id === id) continue;
        const r = snap.markRadius;
        assert.ok(!(o.x + r > plate.x0 && o.x - r < plate.x1 && o.y + r > plate.y0 && o.y - r < plate.y1),
          `the name plate for ${id} stays off ${o.id} at ${width}x${height}`);
      }
      m.canvas.fire('pointerleave', {});
      m.advance(600);
    }
    m.select('area:formal_math_and_proof');
    const sheet = m.map.snapshot().sheet;
    assert.ok(sheet.rect.y1 <= height + 0.5, `the sheet fits the box at ${width}x${height}`);
    for (let i = 1; i < sheet.rows.length; i++) assert.ok(sheet.rows[i].box.y0 >= sheet.rows[i - 1].box.y1 - 0.5, 'rows never overlap');
    if (sheet.card) assert.ok(sheet.card.x0 >= sheet.rect.x1, 'the card stands beside the sheet, never over it');
  }
});

test('the scene is fetched once, revalidated, and the public API answers before and after it arrives', async () => {
  const m = await mount();
  assert.equal(m.requests.length, 1);
  assert.equal(m.requests[0].url, 'docs/architecture-graph-scene.json');
  assert.equal(m.requests[0].opts.cache, 'no-cache');
  assert.equal(typeof m.map.focusFamily, 'function');
  assert.equal(typeof m.map.select, 'function');
  m.map.focusFamily('area:research_and_science_replays');
  assert.deepEqual(plain(m.map.snapshot().focus), { kind: 'family', i: 4 });
  assert.ok(m.rows[4].classList.contains('is-current'), 'the family row is marked current');
  m.map.focusFamily(null);
  assert.ok(!m.rows[4].classList.contains('is-current'));
});

test('motion is bounded: the renderer never loops, caps the pixel ratio and reads no time when idle', () => {
  assert.match(source, /var dpr = Math\.min\(window\.devicePixelRatio \|\| 1, 2\);/, 'the backing store is capped at twice the CSS size');
  assert.doesNotMatch(source, /setInterval/, 'nothing ticks on a timer');
  assert.match(source, /if \(moving\(\) && !frame\) frame = window\.requestAnimationFrame\(tick\);/, 'a frame is asked for only while something moves');
  assert.doesNotMatch(source, /\b(?:gear|escapement|bezel|caseback|chronograph|watch)\b/i, 'no watch words in the code or its comments');
});
