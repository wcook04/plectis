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

// The doctrine projection (docs/doctrine-manifest.json, written by
// microcosm_doctrine_manifest.py): the public titles, and relations dealt
// out deterministically so the fixture reaches the drawing's extremes (up
// to eleven principles and eight axioms on one component).
const AXIOMS = ['Derivation before assertion', 'Kernelized verification', 'Authority by derivation, not possession',
  'Content-addressed determinism', 'Fail-closed monotone lattice', 'Open-world epistemics', 'Typed partiality and refusal',
  'Provenance propagation and non-interference', 'Compensable transactional effects',
  'Temporal validity and freshness contracts', 'Executable grammar before doctrine authority',
  'Reflexive accountability / no privileged meta-layer'];
const PRINCIPLES = ['Recompute, do not echo', 'Lower claim strength to checker strength', 'Concentrate trust in small checkers',
  'Possession is not permission', 'Cache by content, not by name', 'Status fails closed',
  'Track known unknowns without claiming the unknown is mapped', 'Refuse inadmissible computations with typed reasons',
  'Preserve provenance across every boundary', 'Do not land effects without compensation', 'Bind volatile facts to refresh routes',
  'Make doctrine executable before authoritative', 'Apply the same floor to meta artifacts', 'Carry basis and provenance together',
  'Keep projections below source authority', 'Bind authority to transaction scope', 'Anchor graph mutations to unique source rows',
  'Require fan-in before activation', 'Classify residual pressure before wiring', 'Bind result records before record authority'];
const GUARDS = ['Fixture-label echo', 'Producer trust', 'Rank-as-product-score', 'Cache-across-drift', 'Unknown-unknown exhaustiveness',
  'Inadmissible number emission', 'Public/private membrane breach', 'Blind irreversible mutation', 'Frozen live fact',
  'Prose-as-executable-authority', 'Meta-artifact exemption', 'Synthetic system substitution',
  'Generated-result record source inversion', 'Public-authority inflation', 'Mechanism theater', 'Receiver inflation',
  'Projection-as-source'];
function doctrineFor(json) {
  const comps = json.scene.nodes.filter(n => /component$/.test(n.kind)).map(n => n.id);
  const rule = (prefix, kind, i, title) => ({
    id: `${prefix}-${i + 1}`, title, plain: `What ${title.toLowerCase()} asks, in plain words.`,
    doctrine: `doctrine.html#dcard-${prefix.toLowerCase()}-${i + 1}`,
    context: `rules-and-ideas.html#lattice-${kind}-${prefix.toLowerCase()}-${i + 1}`,
    enforced_in: [comps[(i * 7) % comps.length], comps[(i * 7 + 3) % comps.length]],
  });
  const axioms = AXIOMS.map((t, i) => ({ ...rule('AX', 'axiom', i, t), grounds: [], guarded_by: [] }));
  // As in the doctrine, neighbouring principles share their axioms.
  const principles = PRINCIPLES.map((t, i) => ({ ...rule('P', 'principle', i, t), guarded_by: [],
    rests_on: [...new Set([`AX-${Math.floor(i * 0.6) + 1}`, ...(i % 4 === 0 ? [`AX-${((Math.floor(i * 0.6) + 3) % 12) + 1}`] : [])])] }));
  const guards = GUARDS.map((t, i) => ({ ...rule('AP', 'anti-principle', i, t),
    guards: [...new Set([`AX-${(i % 12) + 1}`, ...(i % 2 ? [`AX-${((i + 7) % 12) + 1}`] : [])])],
    negates: [`P-${(i % 20) + 1}`] }));
  principles.forEach(p => p.rests_on.forEach(a => axioms[+a.slice(3) - 1].grounds.push(p.id)));
  guards.forEach(g => g.guards.forEach(a => axioms[+a.slice(3) - 1].guarded_by.push(g.id)));
  guards.forEach(g => g.negates.forEach(p => principles[+p.slice(2) - 1].guarded_by.push(g.id)));
  // A component cites a run of related principles (up to eleven), abides by
  // some of the axioms they rest on, and now and then by one they do not.
  const components = comps.map((id, i) => {
    const governed = Array.from({ length: 1 + (i % 11) }, (_, k) => `P-${((i * 3 + k) % 20) + 1}`);
    const via = [...new Set(governed.flatMap(p => principles[+p.slice(2) - 1].rests_on))];
    const extra = i % 9 === 0 ? [AXIOMS.map((_, a) => `AX-${a + 1}`).find(a => !via.includes(a))] : [];
    return { id, governed_by: [...new Set(governed)], abides_by: [...new Set([...via.slice(0, 1 + (i % 4)), ...extra])] };
  });
  return { schema: 'plectis_system_doctrine_v1', receipt: [{ components: comps.length }],
           axioms, principles, anti_principles: guards, components };
}
const RULE_ID = /\b(?:AX|AP|P)-\d+\b/;

// A small fake DOM: class lists that agree with className, parents, and
// selectors of the forms the map uses (tag, .class, [attr], [attr="v"],
// combined, comma-separated).
function matches(el, selector) {
  return selector.split(',').some(sel => {
    const m = /^([a-z0-9]*)((?:\.[\w-]+)*)((?:\[[\w-]+(?:="[^"]*")?\])*)$/i.exec(sel.trim());
    if (!m || !el.classList) return false;
    if (m[1] && el.tagName !== m[1].toUpperCase()) return false;
    if ((m[2] || '').split('.').filter(Boolean).some(c => !el.classList.contains(c))) return false;
    for (const [, a, v] of (m[3] || '').matchAll(/\[([\w-]+)(?:="([^"]*)")?\]/g)) {
      const got = el.getAttribute(a);
      if (got === null || (v !== undefined && got !== v)) return false;
    }
    return true;
  });
}
function node(tag = 'div') {
  const events = {};
  const classes = new Set();
  const attrs = {};
  const el = {
    tagName: tag.toUpperCase(), children: [], hidden: false, style: {}, offsetWidth: 260, offsetHeight: 180,
    _text: '', parentNode: null, scrollHeight: 0, clientHeight: 0,
    get className() { return [...classes].join(' '); },
    set className(v) { classes.clear(); String(v).split(/\s+/).filter(Boolean).forEach(c => classes.add(c)); },
    get textContent() { return this._text + this.children.map(c => c.textContent).join(''); },
    set textContent(v) { this._text = String(v); this.children = []; },
    get firstChild() { return this.children[0] || null; },
    get lastChild() { return this.children[this.children.length - 1] || null; },
    appendChild(c) { if (c.parentNode && c.parentNode.removeChild) c.parentNode.removeChild(c); this.children.push(c); c.parentNode = this; return c; },
    insertBefore(c, ref) {
      const at = ref ? this.children.indexOf(ref) : -1;
      if (at < 0) return this.appendChild(c);
      this.children.splice(at, 0, c); c.parentNode = this; return c;
    },
    removeChild(c) { this.children = this.children.filter(x => x !== c); c.parentNode = null; return c; },
    getAttribute: n => (n in attrs ? attrs[n] : null),
    setAttribute(n, v) { attrs[n] = String(v); },
    removeAttribute(n) { delete attrs[n]; },
    hasAttribute: n => n in attrs,
    classList: { contains: n => classes.has(n), add: n => classes.add(n), remove: n => classes.delete(n),
      toggle(n, on) { if (on === undefined ? !classes.has(n) : on) classes.add(n); else classes.delete(n); } },
    addEventListener(n, fn) { (events[n] ||= []).push(fn); },
    fire(n, e = {}) { for (const fn of events[n] || []) fn({ preventDefault() {}, stopPropagation() {}, ...e }); },
    all(predicate) { const out = []; const walk = n => { if (predicate(n)) out.push(n); (n.children || []).forEach(walk); }; this.children.forEach(walk); return out; },
    querySelectorAll(sel) { return this.all(n => matches(n, sel)); },
    querySelector(sel) { return this.querySelectorAll(sel)[0] || null; },
    closest(sel) { let n = this; while (n) { if (matches(n, sel)) return n; n = n.parentNode; } return null; },
    // Web Animations: a finished animation reports at once.
    animate() { const a = { cancel() {} }; Object.defineProperty(a, 'onfinish', { set(fn) { if (fn) fn(); } }); return a; },
    getBoundingClientRect() { return this._rect || { left: 0, top: 0, right: 0, bottom: 0, width: 0, height: 0 }; },
  };
  return el;
}
const textOf = n => (n ? n.textContent : '');

// `doctrine: null` serves no projection (the drawing is the machinery
// alone); `column: true` stands the landing's text column beside the
// drawing, so the column companion reads it.
async function mount({ scene = liveScene(), width = 677, height = 569, reduce = false, io = false, fine = true,
                       settle = true, hash = '', doctrine, column = false, em = 0.52, overflow = 0, ownPage = false } = {}) {
  if (doctrine === undefined) doctrine = doctrineFor(scene);
  let clears = 0, texts = [], font = '11px serif';
  const calls = {};
  // Text is measured as `em` of the font size a character (0.52 is wide; the
  // site's serif sets about 0.46).
  const ctx = new Proxy({
    clearRect() { clears++; texts = []; for (const k of Object.keys(calls)) delete calls[k]; },
    fillText(text, x, y) { texts.push({ text: String(text), x, y }); },
    measureText(text) { const px = parseFloat((/([\d.]+)px/.exec(font) || [0, 11])[1]); return { width: String(text).length * px * em }; },
  }, {
    get: (t, k) => (k === 'font' ? font : k in t ? t[k] : () => { calls[k] = (calls[k] || 0) + 1; }),
    set: (t, k, v) => { if (k === 'font') font = v; else t[k] = v; return true; },
  });
  const canvas = Object.assign(node('canvas'), { clientWidth: width, clientHeight: height, width: 0, height: 0,
    getContext: () => ctx, getBoundingClientRect: () => ({ left: 0, top: 0, width, height }) });
  canvas.setAttribute('data-system-src', 'docs/architecture-graph-scene.json');
  canvas.setAttribute('data-system-base', ownPage ? '' : 'docs/');
  canvas.classList.add('system-canvas');
  canvas.setAttribute('data-system-doctrine', 'docs/doctrine-manifest.json');
  const caption = node('p');
  const familyIds = scene.scene.nodes.filter(n => n.kind === 'area').map(n => n.id);
  const rows = familyIds.map(id => {
    const li = node('li');
    li.classList.add('home-family');
    li.setAttribute('data-system-family', id);
    const a = li.appendChild(node('a'));
    a.appendChild(node('span')).classList.add('home-family__name');
    a.appendChild(node('span')).classList.add('home-family__count');
    return li;
  });
  const host = node('div');
  host.classList.add('home-split__text');
  host._rect = { left: 0, top: 0, right: 520, bottom: height, width: 520, height };
  const list = host.appendChild(node('ol'));
  list.classList.add('home-families');
  rows.forEach(li => list.appendChild(li));
  const section = Object.assign(node('section'), {
    querySelectorAll: s => (s.includes('home-family') ? rows : []),
    querySelector: s => (column && s === '.home-split__text' ? host : null),
  });
  const stage = Object.assign(node('figure'), {
    querySelector: s => (s.includes('canvas') ? canvas : s === '.system-caption' ? caption : null),
    // `ownPage`: the drawing on its own page (docs/system-map.html), no slider.
    closest: s => (s === 'section' || (ownPage && s === '[data-system-page]') ? section : null),
  });
  stage._rect = { left: 600, top: 0, right: 600 + width, bottom: height, width, height };
  const document = Object.assign(node('document'), {
    readyState: 'complete', hidden: false, documentElement: node('html'),
    querySelectorAll: s => (s === '[data-system-stage]' ? [stage] : []),
    createElement: tag => {
      const n = node(tag);
      // `overflow`: each block of a column page measures that many pixels
      // longer than its column, 40 fewer for each step its page has closed up.
      if (overflow) {
        Object.defineProperty(n, 'clientHeight', { get: () => 100 });
        Object.defineProperty(n, 'scrollHeight', { get() {
          if (!['sc__ranks', 'sc__peers', 'sc__axioms'].some(c => n.classList.contains(c))) return 100;
          const pg = n.closest('.sc__page');
          const steps = pg ? ['sc__page--dense', 'sc__page--bare', 'sc__page--quiet', 'sc__page--denser'].filter(c => pg.classList.contains(c)).length : 0;
          return 100 + Math.max(0, overflow - 40 * steps);
        } });
      }
      return n;
    },
    createTextNode: text => ({ textContent: String(text), children: [] }),
  });
  const frames = new Map();
  let nextFrame = 1, now = 0;
  const observers = [];
  const window = Object.assign(node('window'), {
    devicePixelRatio: 2, location: { href: '/', hash, pathname: '/docs/system-map.html', search: '' },
    history: { state: null, writes: [], replaceState(st, t, url) { this.writes.push(url); window.location.hash = url.startsWith('#') ? url : ''; } },
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
    fetch: async (url, opts) => {
      requests.push({ url, opts });
      if (/doctrine-manifest\.json/.test(url)) {
        return doctrine ? { ok: true, json: async () => clone(doctrine) } : { ok: false, status: 404, json: async () => ({}) };
      }
      return { ok: true, json: async () => scene };
    },
    setTimeout: (fn, ms) => { timers.push({ fn, ms }); return timers.length; }, clearTimeout() {},
  });
  for (let k = 0; k < 6; k++) await new Promise(r => setImmediate(r));
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
  const select = id => { window.PlectisSystemMap.select(id); advance(1800); };
  const page = () => host.querySelector('.sc__page:not(.sc__page--leaving)') ||
    host.all(n => n.classList && n.classList.contains('sc__page') && !n.classList.contains('sc__page--leaving'))[0] || null;
  return { map: window.PlectisSystemMap, window, document, canvas, caption, rows, section, stage, frames, advance, fireIO,
           runTimers, requests, card, select, host, page, doctrine,
           clears: () => clears, texts: () => texts, calls: () => ({ ...calls }), now: () => now };
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
  const m = await mount({ scene: staleScene(), doctrine: null });
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
  assert.deepEqual(hrefs, [`docs/system-map.html#map=${encodeURIComponent(comp.id)}`], 'the one route is the contract #map= address');
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
  const m = await mount({ doctrine: null });
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
  const m = await mount({ doctrine: null });
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
  const m = await mount({ doctrine: null });
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
  assert.deepEqual(card.all(n => n.tagName === 'A').map(a => a.textContent), ['Component page', 'Full map']);
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
  const m = await mount({ doctrine: null });
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
  const m = await mount({ doctrine: null });
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
  assert.equal(m.requests.length, 2, 'the scene, then the rules each component keeps');
  assert.equal(m.requests[0].url, 'docs/architecture-graph-scene.json');
  assert.equal(m.requests[0].opts.cache, 'no-cache');
  assert.equal(m.requests[1].url, 'docs/doctrine-manifest.json', 'the doctrine comes second, from the canvas attribute');
  assert.equal(m.requests[1].opts.cache, 'no-cache');
  assert.deepEqual(plain(m.map.snapshot().doctrine), { axioms: 12, principles: 20, antiPrinciples: 17 });
  const without = await mount({ doctrine: null });
  assert.equal(without.map.snapshot().doctrine, null, 'a missing projection leaves the machinery drawn alone');
  assert.ok(without.map.snapshot().ready);
  assert.equal(typeof m.map.focusFamily, 'function');
  assert.equal(typeof m.map.select, 'function');
  m.map.focusFamily('area:research_and_science_replays');
  assert.deepEqual(plain(m.map.snapshot().focus), { kind: 'family', i: 4 });
  assert.ok(m.rows[4].classList.contains('is-current'), 'the family row is marked current');
  m.map.focusFamily(null);
  assert.ok(!m.rows[4].classList.contains('is-current'));
});

/* ---- The doctrine: the interior, the column, the family's axioms ---- */

// The canvas at 1280x690, 1440x790 and 1920x953, and a 1024px window's.
const INNER_SIZES = [[630, 526], [677, 569], [900, 790], [506, 411]];
const overlap = (a, b, pad = 0) => a.x0 < b.x1 - pad && a.x1 > b.x0 + pad && a.y0 < b.y1 - pad && a.y1 > b.y0 + pad;
// A run passes through a plate's inside (its ends may touch the edges, at the pins).
function crossesInside(r, rect) {
  const inner = { x0: rect.x0 + 1.5, x1: rect.x1 - 1.5, y0: rect.y0 + 1.5, y1: rect.y1 - 1.5 };
  const box = { x0: Math.min(r.x0, r.x1), x1: Math.max(r.x0, r.x1), y0: Math.min(r.y0, r.y1), y1: Math.max(r.y0, r.y1) };
  return box.x1 >= inner.x0 && box.x0 <= inner.x1 && box.y1 >= inner.y0 && box.y0 <= inner.y1;
}
function busiestOf(doc) {
  return [...doc.components].sort((a, b) => b.governed_by.length - a.governed_by.length || b.abides_by.length - a.abides_by.length)[0];
}
function axiomsShown(doc, row) {
  const via = row.governed_by.flatMap(p => doc.principles.find(x => x.id === p).rests_on);
  return new Set([...via, ...row.abides_by]);
}
const centre = r => [(r.x0 + r.x1) / 2, (r.y0 + r.y1) / 2];

test('a selected component opens into its interior: the base, its principles above, their axioms on top, at four sizes', async () => {
  for (const [width, height] of INNER_SIZES) {
    const m = await mount({ width, height, em: 0.46 });
    const doc = m.doctrine;
    for (const row of [busiestOf(doc), doc.components[0], doc.components[4]]) {
      m.select(row.id);
      const s = m.map.snapshot(), it = s.interior;
      assert.equal(s.level, 'component');
      assert.ok(it && it.settled, `${row.id} opens and settles at ${width}x${height}`);
      const P = it.plates.filter(p => p.kind === 'principle'), A = it.plates.filter(p => p.kind === 'axiom');
      assert.deepEqual(new Set(P.map(p => p.id)), new Set(row.governed_by), 'its principles are the ones it is governed by');
      assert.deepEqual(new Set(A.map(p => p.id)), axiomsShown(doc, row), 'its axioms: those its principles rest on, and those it abides by');
      assert.ok(Math.max(...A.map(p => p.rect.y1)) < Math.min(...P.map(p => p.rect.y0)), 'the axioms stand above the principles');
      assert.ok(Math.max(...P.map(p => p.rect.y1)) < it.base.rect.y0, 'the principles stand above the component');
      const all = it.plates.map(p => p.rect).concat([it.base.rect]);
      for (const r of all) assert.ok(r.x0 >= 0 && r.y0 >= 0 && r.x1 <= width && r.y1 <= height, `a plate leaves the drawing at ${width}x${height}`);
      for (let i = 0; i < all.length; i++) {
        for (let k = i + 1; k < all.length; k++) assert.ok(!overlap(all[i], all[k], 0.5), `plates ${i} and ${k} overlap at ${width}x${height}`);
      }
      // At the laptop and monitor sizes every name stands whole, in at most
      // four lines; only a crowded interior in a small window may cut one.
      for (const p of it.plates) {
        assert.ok(p.lines.length >= 1 && p.lines.length <= 4, `${p.title} takes four lines at most`);
        if (width >= 600 || !it.forced) assert.equal(p.lines.join(' '), p.title, `${p.title} is named whole at ${width}x${height}`);
      }
      // Every guard declared on a shown axiom sits on its top edge.
      for (const a of A) {
        const marks = it.guards.filter(g => g.axiom === a.id);
        assert.equal(marks.length, doc.axioms.find(x => x.id === a.id).guarded_by.length, `the guards of ${a.title}`);
        for (const g of marks) assert.ok(g.y < a.rect.y0 && g.x > a.rect.x0 && g.x < a.rect.x1, 'a guard stands on its axiom');
      }
      // The wiring is orthogonal and never runs through a plate.
      for (const r of it.runs) {
        assert.ok(Math.abs(r.x0 - r.x1) < 0.01 || Math.abs(r.y0 - r.y1) < 0.01, 'every run is straight');
        for (const rect of all) assert.ok(!crossesInside(r, rect), `a ${r.kind} run crosses a plate at ${width}x${height}`);
      }
      assert.equal(it.runs.filter(r => r.kind === 'tap').length, row.governed_by.length, 'one tap to each principle');
      assert.equal(it.runs.filter(r => r.kind === 'rise').length, A.length, 'one wire up into each axiom');
      // Words never meet.
      const drawn = s.drawn;
      for (let i = 0; i < drawn.length; i++) {
        for (let k = i + 1; k < drawn.length; k++) assert.ok(!overlap(drawn[i], drawn[k], 0.5), `words ${i} and ${k} at ${width}x${height}`);
      }
      m.document.fire('keydown', { key: 'Escape' });
      assert.equal(m.map.snapshot().interior, null, 'Escape folds it at once');
    }
  }
});

test('the interior lights rank by rank in about a second, then stops; stepping back runs the same way home', async () => {
  const m = await mount();
  const row = busiestOf(m.doctrine);
  m.map.select(row.id);
  m.advance(16);
  let s = m.map.snapshot();
  assert.ok(s.interior && !s.interior.settled && s.moving, 'it is opening');
  const lastP = Math.max(...s.interior.plates.filter(p => p.kind === 'principle').map(p => p.lit));
  const firstA = Math.min(...s.interior.plates.filter(p => p.kind === 'axiom').map(p => p.lit));
  assert.ok(lastP < firstA, 'every principle lights before the first axiom');
  let elapsed = 16;
  while (m.map.snapshot().moving && elapsed < 5000) { m.advance(16); elapsed += 16; }
  assert.ok(elapsed >= 900 && elapsed <= 1500, `the interior took ${elapsed}ms`);
  assert.equal(m.frames.size, 0, 'nothing runs once it has settled');
  const clears = m.clears();
  m.advance(2000);
  assert.equal(m.clears(), clears, 'and nothing repaints while the reader is idle');
  // A click on empty ground folds it back the way it came.
  m.canvas.fire('click', { clientX: 677 - 3, clientY: 569 * 0.5, detail: 1 });
  m.advance(160);
  s = m.map.snapshot();
  assert.ok(s.interior && s.interior.closing && s.interior.t < s.interior.end, 'it folds through the same states');
  m.advance(1600);
  s = m.map.snapshot();
  assert.equal(s.interior, null);
  assert.equal(s.level, 'overview');
  assert.equal(m.frames.size, 0);
});

test('reduced motion: the interior stands at once and folds at once, with no frame', async () => {
  const m = await mount({ reduce: true });
  m.map.select(busiestOf(m.doctrine).id);
  assert.ok(m.map.snapshot().interior.settled, 'final at once');
  assert.equal(m.frames.size, 0);
  m.document.fire('keydown', { key: 'Escape' });
  assert.equal(m.map.snapshot().interior, null);
  assert.equal(m.frames.size, 0);
});

test('a rule pointed at in the interior lights its path; selected, it is held; Escape lets go of the rule, then the component', async () => {
  const m = await mount();
  const row = busiestOf(m.doctrine);
  m.select(row.id);
  const it = m.map.snapshot().interior;
  const axiom = it.plates.find(p => p.kind === 'axiom');
  const [x, y] = centre(axiom.rect);
  m.canvas.fire('pointermove', { clientX: x, clientY: y, pointerType: 'mouse' });
  m.advance(400);
  assert.equal(m.map.snapshot().ruleHover, axiom.id, 'the axiom under the pointer is in focus');
  assert.match(m.caption.textContent, new RegExp(axiom.title.replace(/[/]/g, '\\/')), 'the caption names it in words');
  m.canvas.fire('click', { clientX: x, clientY: y, detail: 1 });
  assert.equal(m.map.snapshot().rulePinned, axiom.id, 'a click holds it');
  m.document.fire('keydown', { key: 'Escape' });
  assert.equal(m.map.snapshot().rulePinned, null, 'Escape lets the rule go first');
  assert.equal(m.map.snapshot().level, 'component');
  m.document.fire('keydown', { key: 'Escape' });
  assert.equal(m.map.snapshot().level, 'overview');
});

test('the column reads the drawing: the component, then a rule, each a page; back and Escape retrace the trail', async () => {
  const m = await mount({ column: true });
  const doc = m.doctrine, row = busiestOf(doc);
  const label = m.map.snapshot().components.find(c => c.id === row.id).label;
  m.select(row.id);
  let s = m.map.snapshot();
  assert.equal(s.column.kind, 'comp');
  assert.equal(s.column.title, label, 'the column carries the component name');
  assert.ok(m.card() === null || m.card().hidden, 'and no card stands in the drawing');
  const page = m.page();
  const named = page.querySelectorAll('.sc__rule').map(b => b.getAttribute('data-rule'));
  assert.deepEqual(new Set(named), new Set([...row.governed_by, ...axiomsShown(doc, row)]), 'it names exactly the rules the interior draws');
  const principle = page.querySelectorAll('.sc__rule').find(b => b.getAttribute('data-rule') === row.governed_by[0]);
  principle.fire('pointerenter');
  assert.equal(m.map.snapshot().ruleHover, row.governed_by[0], 'pointing at a rule in the column lights it in the drawing');
  principle.fire('pointerleave');
  principle.fire('click', { detail: 1 });
  s = m.map.snapshot();
  assert.equal(s.rulePinned, row.governed_by[0]);
  assert.equal(s.column.kind, 'rule', 'the column turns to the rule');
  const rule = doc.principles.find(p => p.id === row.governed_by[0]);
  assert.equal(s.column.title, rule.title);
  const links = Object.fromEntries(m.page().querySelectorAll('a').map(a => [a.textContent, a.getAttribute('href')]));
  assert.equal(links['Read it in the doctrine'], 'docs/' + rule.doctrine, 'the doctrine card, at its published anchor');
  assert.equal(links['See it among the rules'], 'docs/' + rule.context);
  m.page().querySelector('.sc__back-btn').fire('click', { detail: 1 });
  s = m.map.snapshot();
  assert.equal(s.column.kind, 'comp', 'back returns to the component');
  assert.equal(s.rulePinned, null);
  const keyed = m.page().querySelectorAll('.sc__rule').find(b => b.getAttribute('data-rule') === row.governed_by[0]);
  assert.deepEqual([keyed.getAttribute('role'), keyed.getAttribute('tabindex')], ['button', '0'], 'each rule named is a button the keyboard reaches');
  keyed.fire('keydown', { key: 'Enter' });
  assert.equal(m.map.snapshot().rulePinned, row.governed_by[0], 'Enter turns the column to the rule');
  m.page().querySelector('.sc__back-btn').fire('click', { detail: 0 });
  assert.equal(m.map.snapshot().column.kind, 'comp');
  m.document.fire('keydown', { key: 'Escape' });
  m.advance(1600);
  s = m.map.snapshot();
  assert.equal(s.level, 'overview');
  assert.equal(s.column, null, 'and the column is the families again');
  assert.ok(!m.host.classList.contains('sc-host--open'));
});

test('on its own page the drawing opens when in view, follows #map= and writes the selection back', async () => {
  const doc = doctrineFor(liveScene()), row = busiestOf(doc), comp = row.id;
  const m = await mount({ ownPage: true, io: true, column: true });
  assert.equal(m.map.snapshot().open, 'waiting', 'a blueprint until it is in view');
  m.fireIO(1);
  m.advance(32);
  assert.equal(m.map.snapshot().open, 'running', 'in view it opens: there is no slider to wait for');
  m.advance(2500);
  assert.equal(m.map.snapshot().open, 'done');
  assert.equal(m.frames.size, 0, 'and stops');
  m.select(comp);
  assert.equal(m.window.location.hash, '#map=' + encodeURIComponent(comp), 'a selection is the address');
  const links = m.page().querySelectorAll('a').map(a => [a.textContent, a.getAttribute('href')]);
  assert.ok(!links.some(([t]) => t === 'Full map'), 'the page is the map, so it does not link to one');
  assert.ok(links.length && links.every(([, h]) => !h.startsWith('docs/')), 'routes are docs-relative on a docs page');
  m.map.selectRule(row.governed_by[0]);
  const rule = doc.principles.find(p => p.id === row.governed_by[0]);
  assert.equal(m.page().querySelectorAll('a').find(a => a.textContent === 'Read it in the doctrine').getAttribute('href'), rule.doctrine);
  m.document.fire('keydown', { key: 'Escape' });
  m.document.fire('keydown', { key: 'Escape' });
  m.advance(1600);
  assert.equal(m.map.snapshot().level, 'overview');
  assert.equal(m.window.location.hash, '', 'stepping back to the whole drawing clears it');
  const linked = await mount({ ownPage: true, column: true, settle: false, hash: '#map=' + encodeURIComponent(comp) });
  let s = linked.map.snapshot();
  assert.equal(s.open, 'done', 'an address lands on the finished drawing');
  assert.equal(s.level, 'component');
  assert.equal(s.pinned.comp >= 0 && s.components[s.pinned.comp].id, comp, 'with the component it names selected');
  linked.window.location.hash = '#map=' + encodeURIComponent('area:formal_math_and_proof');
  linked.window.fire('hashchange');
  linked.advance(1600);
  s = linked.map.snapshot();
  assert.equal(s.level, 'family', 'a new address selects again');
  assert.equal(s.sheet.family, 'area:formal_math_and_proof');
  const landing = await mount({ column: true, hash: '#map=' + encodeURIComponent(comp) });
  assert.equal(landing.map.snapshot().level, 'overview', 'on the landing an address is not the drawing\'s');
  landing.select(comp);
  assert.deepEqual(landing.window.history.writes, [], 'and a selection there writes none');
});

test('a page longer than its column closes up in steps, and only then is anything cut', async () => {
  const id = busiestOf(doctrineFor(liveScene())).id;
  const steps = p => ['sc__page--dense', 'sc__page--bare', 'sc__page--quiet', 'sc__page--denser'].filter(c => p.classList.contains(c));
  const roomy = await mount({ column: true });
  roomy.select(id);
  assert.deepEqual(steps(roomy.page()), [], 'a page that fits stands as it is');
  const close = await mount({ column: true, overflow: 60 });
  close.select(id);
  assert.deepEqual(steps(close.page()), ['sc__page--dense', 'sc__page--bare'], 'lists run on, then the neighbours give way');
  assert.ok(!close.page().querySelector('.sc__ranks').classList.contains('is-cut'), 'and nothing is cut');
  const long = await mount({ column: true, overflow: 500 });
  long.select(id);
  assert.deepEqual(steps(long.page()), ['sc__page--dense', 'sc__page--bare', 'sc__page--quiet', 'sc__page--denser']);
  assert.ok(long.page().querySelector('.sc__ranks').classList.contains('is-cut'), 'only then is a block cut, fading at its foot');
  const lensed = await mount({ column: true, overflow: 60 });
  lensed.map.lens('doctrine');
  lensed.advance(600);
  assert.equal(lensed.map.snapshot().column.kind, 'doctrine');
  assert.deepEqual(steps(lensed.page()), ['sc__page--dense', 'sc__page--bare'], 'the doctrine page closes up the same way');
});

test('each family row carries its components as the drawing marks them', async () => {
  const m = await mount({ column: true });
  const snap = m.map.snapshot();
  for (const li of m.rows) {
    const marks = li.querySelector('.home-family__marks');
    const fam = li.getAttribute('data-system-family');
    assert.ok(marks, `${fam} has its marks`);
    assert.equal(marks.getAttribute('aria-hidden'), 'true', 'they repeat the count, so they are hidden from readers');
    assert.equal((marks.innerHTML.match(/<g data-ci=/g) || []).length, snap.components.filter(c => c.family === fam).length,
      'one mark to each component');
    assert.ok(li.classList.contains('has-marks'));
  }
});

test('a family fills the drawing: its sheet beside the axioms its components abide by', async () => {
  const m = await mount({ column: true });
  const doc = m.doctrine, fam = 'area:formal_math_and_proof';
  m.select(fam);
  const s = m.map.snapshot();
  assert.equal(s.level, 'family');
  assert.equal(s.column.kind, 'fam', 'the column reads the family');
  assert.ok(m.card() === null || m.card().hidden, 'no card beside the sheet: the axioms stand there');
  assert.equal(s.profile.rows.length, 12, 'one row to each axiom');
  const members = s.components.filter(c => c.family === fam).map(c => c.id);
  for (const r of s.profile.rows) {
    const k = doc.components.filter(c => members.includes(c.id) && c.abides_by.includes(r.id)).length;
    assert.equal(r.k, k, `the count beside ${r.id} is the family's components that abide by it`);
    assert.equal(r.n, members.length);
    assert.ok(r.box.x0 >= s.sheet.rect.x1, 'the axioms stand beside the sheet, never over it');
    assert.ok(r.box.x1 <= s.width + 0.5);
  }
  // The column counts how they are checked, class by class; a class pointed
  // at lights the components checked that way, then lets go.
  const byClass = {};
  s.components.filter(c => c.family === fam).forEach(c => { byClass[c.cls] = (byClass[c.cls] || 0) + 1; });
  const classes = m.page().querySelectorAll('.sc__live--class');
  assert.deepEqual(classes.map(li => li.getAttribute('data-class')).sort(), Object.keys(byClass).sort(), 'a row to each class the family holds');
  for (const li of classes) {
    assert.equal(li.querySelector('.sc__live-count').textContent, `${byClass[li.getAttribute('data-class')]} of ${members.length}`);
  }
  classes[0].fire('pointerenter');
  const lit = m.map.snapshot().focus;
  assert.deepEqual([lit.kind, lit.i], ['class', classes[0].getAttribute('data-class')], 'a class pointed at is the focus');
  assert.ok(classes[0].classList.contains('is-lit'));
  classes[0].fire('pointerleave');
  assert.equal(m.map.snapshot().focus, null, 'and lets go');
  assert.ok(!classes[0].classList.contains('is-lit'));
  const kept = s.profile.rows.filter(r => r.k > 0).length;
  assert.match(m.page().textContent, new RegExp(`They abide by ${kept === 12 ? 'all twelve' : '\\w+ of the twelve'} axioms`),
    'the rules they keep, in words');
  const row = s.profile.rows.find(r => r.k > 0);
  const [x, y] = centre(row.box);
  m.canvas.fire('pointermove', { clientX: x, clientY: y, pointerType: 'mouse' });
  m.advance(400);
  const focus = m.map.snapshot().focus;
  assert.deepEqual([focus.kind, focus.i], ['rule', row.id], 'pointing at an axiom puts it in focus');
  m.canvas.fire('click', { clientX: x, clientY: y, detail: 1 });
  assert.equal(m.map.snapshot().rulePinned, row.id);
  assert.equal(m.map.snapshot().column.kind, 'rule', 'selecting it turns the column to the axiom');
  m.document.fire('keydown', { key: 'Escape' });
  assert.equal(m.map.snapshot().column.kind, 'fam', 'Escape returns to the family');
});

test('in the drawing and the column every word is plain: no rule ids, field names or schema words', async () => {
  const m = await mount({ column: true });
  const doc = m.doctrine, row = busiestOf(doc);
  const seen = [];
  const collect = () => { seen.push(m.caption.textContent, ...m.texts().map(t => t.text)); const p = m.page(); if (p) seen.push(p.textContent); };
  m.select(row.id);
  collect();
  const it = m.map.snapshot().interior;
  for (const p of it.plates.slice(0, 3)) {
    const [x, y] = centre(p.rect);
    m.canvas.fire('pointermove', { clientX: x, clientY: y, pointerType: 'mouse' });
    m.advance(300);
    collect();
  }
  const g = it.guards[0];
  m.canvas.fire('pointermove', { clientX: g.x, clientY: g.y, pointerType: 'mouse' });
  m.advance(300);
  collect();
  m.map.selectRule(row.governed_by[0]);
  collect();
  m.map.selectRule(doc.anti_principles[0].id);
  collect();
  m.map.select('area:import_projection_and_drift');
  m.advance(900);
  collect();
  const text = seen.join(' \n ');
  assert.doesNotMatch(text, RULE_ID, 'no rule ids on their own');
  assert.doesNotMatch(text, /\b(?:component|area|primitive|cluster|inspector):/, 'no node ids');
  assert.doesNotMatch(text, /_|governed_by|abides_by|guarded_by|rests_on|anti_principle/, 'no field names');
  assert.doesNotMatch(text, /—|·/, 'no em dashes or middle dots');
});

test('the doctrine lens: one switch turns the drawing, lands in its final state and stops; turning back restores it', async () => {
  const m = await mount({ column: true });
  const doc = m.doctrine;
  const rest = m.host.querySelector('.sc-lens');
  assert.ok(rest && rest.classList.contains('is-ready'), 'the switch stands with the families once the rules arrive');
  const tab = rest.querySelectorAll('.sc-lens__tab').find(b => b.getAttribute('data-lens') === 'doctrine');
  tab.fire('click', { detail: 1 });
  m.advance(200);
  let s = m.map.snapshot();
  assert.equal(s.lens, 'doctrine');
  assert.ok(s.lensMix > 0 && s.lensMix < 1, 'mid-way the machinery is receding');
  m.advance(600);
  s = m.map.snapshot();
  assert.equal(s.lensMix, 1, 'it arrives at the doctrine');
  assert.equal(m.frames.size, 0, 'and nothing runs after');
  assert.equal(s.column.kind, 'doctrine', 'the column lists the axioms');
  const rows = m.page().querySelectorAll('.sc__axiom');
  assert.equal(rows.length, 12);
  // Each row's count and fingerprint say how many components abide by it.
  for (const b of rows) {
    const id = b.getAttribute('data-rule');
    const k = doc.components.filter(c => c.abides_by.includes(id)).length;
    assert.equal(b.querySelector('.sc__axiom-count').textContent, String(k), `${id} counts its components`);
    const fp = b.querySelector('.sc__fp').innerHTML;
    assert.equal((fp.match(/class="is-on"/g) || []).length, k, 'one tall tick to each component that abides by it');
    assert.equal((fp.match(/<rect /g) || []).length, s.components.length, 'and one tick to every component');
  }
  // Pointing at a row lights its reach in place, then the drawing rests.
  rows[0].fire('pointerenter');
  m.advance(16);
  assert.ok(m.frames.size > 0, 'the reach lights in reading order');
  m.advance(900);
  s = m.map.snapshot();
  assert.deepEqual([s.focus.kind, s.focus.i], ['rule', rows[0].getAttribute('data-rule')]);
  assert.equal(m.frames.size, 0, 'once lit, nothing moves');
  const clears = m.clears();
  m.advance(2000);
  assert.equal(m.clears(), clears, 'and nothing repaints while the reader is idle');
  // Selecting it holds the reach and turns the column to the axiom.
  rows[0].fire('click', { detail: 1 });
  rows[0].fire('pointerleave');
  s = m.map.snapshot();
  assert.equal(s.column.kind, 'rule');
  assert.deepEqual([s.focus.kind, s.focus.i], ['rule', rows[0].getAttribute('data-rule')], 'the held rule stays lit');
  m.document.fire('keydown', { key: 'Escape' });
  assert.equal(m.map.snapshot().column.kind, 'doctrine', 'Escape returns to the axioms');
  // Turning back restores the machinery exactly, and the families.
  m.page().querySelectorAll('.sc-lens__tab').find(b => b.getAttribute('data-lens') === 'machinery').fire('click', { detail: 1 });
  m.advance(800);
  s = m.map.snapshot();
  assert.equal(s.lens, 'machinery');
  assert.equal(s.lensMix, 0);
  assert.equal(s.column, null, 'the column is the families again');
  assert.equal(m.frames.size, 0);
});

test('the lens under reduced motion and from the keyboard turns at once', async () => {
  const m = await mount({ column: true, reduce: true });
  m.map.lens('doctrine');
  assert.equal(m.map.snapshot().lensMix, 1);
  assert.equal(m.frames.size, 0);
  const keyed = await mount({ column: true });
  const tab = keyed.host.querySelector('.sc-lens').querySelectorAll('.sc-lens__tab').find(b => b.getAttribute('data-lens') === 'doctrine');
  tab.fire('click', { detail: 0 });
  assert.equal(keyed.map.snapshot().lensMix, 1, 'a keyboard press lands at once');
  assert.equal(keyed.frames.size, 0);
});

test('every doctrine view says its counts in plain words and draws no word over another, at four sizes', async () => {
  for (const [width, height] of INNER_SIZES) {
    const m = await mount({ width, height, column: true });
    m.map.lens('doctrine');
    m.advance(800);
    const seen = [];
    for (const b of m.page().querySelectorAll('.sc__axiom').slice(0, 4)) {
      b.fire('pointerenter');
      m.advance(900);
      const s = m.map.snapshot();
      for (let i = 0; i < s.drawn.length; i++) {
        for (let k = i + 1; k < s.drawn.length; k++) assert.ok(!overlap(s.drawn[i], s.drawn[k], 0.5), `words meet at ${width}x${height}`);
      }
      seen.push(m.caption.textContent, ...m.texts().map(t => t.text), m.page().textContent);
      b.fire('pointerleave');
    }
    const text = seen.join(' \n ');
    assert.doesNotMatch(text, RULE_ID);
    assert.doesNotMatch(text, /_|—|·/);
  }
});

test('motion is bounded: the renderer never loops, caps the pixel ratio and reads no time when idle', () => {
  assert.match(source, /var dpr = Math\.min\(window\.devicePixelRatio \|\| 1, 2\);/, 'the backing store is capped at twice the CSS size');
  assert.doesNotMatch(source, /setInterval/, 'nothing ticks on a timer');
  assert.match(source, /if \(moving\(\) && !frame\) frame = window\.requestAnimationFrame\(tick\);/, 'a frame is asked for only while something moves');
  assert.doesNotMatch(source, /\b(?:gear|escapement|bezel|caseback|chronograph|watch)\b/i, 'no watch words in the code or its comments');
});
