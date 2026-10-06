// The system map (assets/system-map.js, the circle, 2026-10-04): run in a vm
// against the published architecture scene and a doctrine projection, with a
// small fake DOM whose boxes are laid out deterministically, so every view's
// words, lines and addresses can be checked without a browser. The geometry
// at real sizes (no overlaps, no clipping, type sizes) is audited in Chrome by
// the capture scripts; these tests pin the data, the relations drawn (and only
// those), the words, the levels, the addresses and the keyboard.
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import vm from 'node:vm';

const source = readFileSync(new URL('../assets/system-map.js', import.meta.url), 'utf8');
// SYSTEM_MAP_SCENE and SYSTEM_MAP_DOCTRINE name other data files to run the
// same tests against (a regenerated scene or manifest, before it is published).
const SCENE_PATH = process.env.SYSTEM_MAP_SCENE || new URL('../docs/architecture-graph-scene.json', import.meta.url);
const DOCTRINE_PATH = process.env.SYSTEM_MAP_DOCTRINE || new URL('../docs/doctrine-manifest.json', import.meta.url);
const sceneFile = JSON.parse(readFileSync(SCENE_PATH, 'utf8'));
const clone = value => JSON.parse(JSON.stringify(value));
const plain = value => JSON.parse(JSON.stringify(value));

const CLASSES = [
  ['external_subprocess_witness', 'External tool run', 4, true, 'Real runtime result'],
  ['bounded_runtime_computation', 'Bounded runtime computation', 4, true, 'Real runtime result'],
  ['verified_macro_body_import', 'Verified source import', 5, false, 'Copied source body'],
  ['semantic_validator', 'Contract validator', 5, false, 'Import validation'],
  ['algorithmic_projection', 'Computed projection', 3, false, 'Source-faithful refactor'],
];

// The scene as the deploy publishes it, with per-object details. A checkout
// whose scene predates the details gets them synthesised, deterministically,
// including the prose the column trims (one sentence carries a file name, as
// some published ones do, and must never be shown).
const CODE_RELATIONS = ['runs', 'reads_results_of', 'checks_copies_of'];
const codeEdges = json => json.scene.edges.filter(e => CODE_RELATIONS.includes(e.relation));
// Most tests pin the older shape of scene, whose links are the relations a
// component's own record lists (still drawn, without direction). A scene
// derived from the code has none, so for those tests they are made up from
// its components, deterministically, in place of its code connections: each
// component lists a few others, the first a dozen, the last none.
function withListedRelations(json) {
  const scene = json.scene;
  if (declared(json).length) return json;
  const ids = compNodes(json).map(n => n.id), n = ids.length - 1, seen = new Set(), made = [];
  const add = (a, b) => {
    if (a === b || a === ids[n] || b === ids[n] || seen.has(a + '>' + b)) return;
    seen.add(a + '>' + b);
    made.push({ id: 'edge:declared:' + made.length, source: a, target: b, relation: 'declared_dependency_untyped', kind: 'declared_dependency_untyped' });
  };
  ids.slice(0, n).forEach((a, i) => { add(a, ids[(i * 7 + 3) % n]); if (i % 2 === 0) add(a, ids[(i * 13 + 5) % n]); });
  for (let j = 1; j <= 12; j++) add(ids[0], ids[(j * 5) % n]);
  scene.edges = scene.edges.filter(e => !CODE_RELATIONS.includes(e.relation)).concat(made);
  delete json.edge_semantics;
  return json;
}
function liveScene() { return withListedRelations(detailedScene()); }
function detailedScene() {
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
        what_it_does: `It reads its inputs and checks them. It writes one record per check. It loads helper_module.py before it runs. It stops there.`,
        links_note: `composition root naming some_component_id and another_one`,
        evidence: { class_id, kind, rank, runs_real_tools: runs, basis },
        source_links: [{ label: 'Design note', url: `https://example.org/${slug}.md` }, { label: 'Source', url: `https://example.org/${slug}.py` }],
        routes: { component_detail_href: `component-${slug}.html`, primary_reader_href: `paper-module-${slug}.html`,
                  map_href: `architecture.html#map=${encodeURIComponent(n.id)}` },
      };
    } else if (n.kind === 'area') {
      scene.inspectors[ref] = { title: n.label, summary: `What the ${n.label} family is for, in plain words.`,
        routes: { primary_reader_href: n.resolver_ref.replace(/^docs\//, ''), map_href: `architecture.html#map=${encodeURIComponent(n.id)}` } };
    } else {
      scene.inspectors[ref] = { title: n.label, routes: {} };
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
const compNodes = json => json.scene.nodes.filter(n => /component$/.test(n.kind));
const famOf = json => Object.fromEntries(compNodes(json).map(n => [n.id, n.parent_cluster_id.replace('cluster:', '')]));

// The doctrine projection (docs/doctrine-manifest.json, written by
// microcosm_doctrine_manifest.py at deploy): the public titles, and relations
// dealt out deterministically so a component cites some principles, some
// axioms its principles do not rest on, and enforces rules it does not cite.
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
const FAILURES = ['Fixture-label echo', 'Producer trust', 'Rank-as-product-score', 'Cache-across-drift', 'Unknown-unknown exhaustiveness',
  'Inadmissible number emission', 'Public/private membrane breach', 'Blind irreversible mutation', 'Frozen live fact',
  'Prose-as-executable-authority', 'Meta-artifact exemption', 'Synthetic system substitution',
  'Generated-result record source inversion', 'Public-authority inflation', 'Mechanism theater', 'Receiver inflation',
  'Projection-as-source'];
function doctrineFor(json) {
  const comps = compNodes(json).map(n => n.id);
  const rule = (prefix, i, title) => ({
    id: `${prefix}-${i + 1}`, title, plain: `What ${title.toLowerCase()} asks, in plain words.`,
    doctrine: `doctrine.html#dcard-${prefix.toLowerCase()}-${i + 1}`,
    enforced_in: [comps[(i * 7) % comps.length], comps[(i * 7 + 3) % comps.length]],
  });
  const axioms = AXIOMS.map((t, i) => ({ ...rule('AX', i, t), grounds: [], guarded_by: [] }));
  const principles = PRINCIPLES.map((t, i) => ({ ...rule('P', i, t), guarded_by: [],
    rests_on: [...new Set([`AX-${Math.floor(i * 0.6) + 1}`, ...(i % 4 === 0 ? [`AX-${((Math.floor(i * 0.6) + 3) % 12) + 1}`] : [])])] }));
  const failures = FAILURES.map((t, i) => ({ ...rule('AP', i, t),
    guards: [...new Set([`AX-${(i % 12) + 1}`, ...(i % 2 ? [`AX-${((i + 7) % 12) + 1}`] : [])])],
    negates: [`P-${(i % 20) + 1}`] }));
  principles.forEach(p => p.rests_on.forEach(a => axioms[+a.slice(3) - 1].grounds.push(p.id)));
  failures.forEach(g => g.guards.forEach(a => axioms[+a.slice(3) - 1].guarded_by.push(g.id)));
  failures.forEach(g => g.negates.forEach(p => principles[+p.slice(2) - 1].guarded_by.push(g.id)));
  const components = comps.map((id, i) => {
    const governed = Array.from({ length: 1 + (i % 9) }, (_, k) => `P-${((i * 3 + k) % 20) + 1}`);
    const via = [...new Set(governed.flatMap(p => principles[+p.slice(2) - 1].rests_on))];
    const extra = i % 5 === 0 ? [AXIOMS.map((_, a) => `AX-${a + 1}`).find(a => !via.includes(a))] : [];
    return { id, governed_by: [...new Set(governed)], abides_by: [...new Set([...via.slice(0, 1 + (i % 3)), ...extra])] };
  });
  return { schema: 'plectis_system_doctrine_v1', receipt: [{ components: comps.length }],
           axioms, principles, anti_principles: failures, components };
}
const RULE_ID = /\b(?:AX|AP|P)-\d+\b/;
const UNPLAIN = /—|\b[a-z0-9]+_[a-z0-9_]+\b|\b(?:AX|AP|P)-\d+\b|links_note|governed_by|abides_by|enforced_in|rests_on/;

/* ---- A small DOM --------------------------------------------------------- */
// Elements with class lists that agree with className, attributes (hidden
// reflected), parents and siblings, listeners, and selectors of the forms
// the map uses: tag, .class, [attr], [attr="v"], compounds, lists and the
// descendant combinator. Boxes are laid out deterministically from creation
// order so every measured line has two distinct ends.
function matchesOne(el, sel) {
  const m = /^([a-z0-9]*)((?:\.[\w-]+)*)((?:\[[\w-]+(?:="[^"]*")?\])*)$/i.exec(sel.trim());
  if (!m || !el || !el.classList) return false;
  if (m[1] && el.tagName !== m[1].toUpperCase()) return false;
  if ((m[2] || '').split('.').filter(Boolean).some(c => !el.classList.contains(c))) return false;
  for (const [, a, v] of (m[3] || '').matchAll(/\[([\w-]+)(?:="([^"]*)")?\]/g)) {
    const got = el.getAttribute(a);
    if (got === null || (v !== undefined && got !== v)) return false;
  }
  return true;
}
function matches(el, selector) {
  return selector.split(',').some(sel => {
    const parts = sel.trim().split(/\s+/);
    if (!matchesOne(el, parts[parts.length - 1])) return false;
    let at = el.parentNode;
    for (let k = parts.length - 2; k >= 0; k--) {
      while (at && !matchesOne(at, parts[k])) at = at.parentNode;
      if (!at) return false;
      at = at.parentNode;
    }
    return true;
  });
}
function makeDom() {
  let seq = 0;
  const animations = [];
  const doc = {};
  function node(tag = 'div') {
    const events = {};
    const classes = new Set();
    const attrs = {};
    const style = { setProperty(k, v) { this[k] = String(v); }, removeProperty(k) { delete this[k]; } };
    const n = seq++;
    const el = {
      tagName: tag.toUpperCase(), children: [], style, parentNode: null, _text: '', inert: false, disabled: false,
      scrollHeight: 0, clientHeight: 0, scrollTop: 0, offsetWidth: 120, offsetHeight: 24, seq: n,
      get hidden() { return 'hidden' in attrs; },
      set hidden(v) { if (v) attrs.hidden = ''; else delete attrs.hidden; },
      get className() { return [...classes].join(' '); },
      set className(v) { classes.clear(); String(v).split(/\s+/).filter(Boolean).forEach(c => classes.add(c)); },
      get textContent() { return this._text + this.children.map(c => c.textContent).join(''); },
      set textContent(v) { this._text = String(v); this.children.forEach(c => { c.parentNode = null; }); this.children = []; },
      set innerHTML(v) { this._html = String(v); },
      get innerHTML() { return this._html || ''; },
      get firstChild() { return this.children[0] || null; },
      get lastChild() { return this.children[this.children.length - 1] || null; },
      get nextSibling() { if (!this.parentNode) return null; const s = this.parentNode.children; return s[s.indexOf(this) + 1] || null; },
      appendChild(c) { if (c.parentNode) c.parentNode.removeChild(c); this.children.push(c); c.parentNode = this; return c; },
      insertBefore(c, ref) {
        if (c.parentNode) c.parentNode.removeChild(c);
        const at = ref ? this.children.indexOf(ref) : -1;
        if (at < 0) { this.children.push(c); } else { this.children.splice(at, 0, c); }
        c.parentNode = this;
        return c;
      },
      removeChild(c) { this.children = this.children.filter(x => x !== c); c.parentNode = null; return c; },
      getAttribute: a => (a === 'class' ? (classes.size ? [...classes].join(' ') : null) : a in attrs ? attrs[a] : null),
      setAttribute(a, v) { if (a === 'class') this.className = v; else attrs[a] = String(v); },
      removeAttribute(a) { if (a === 'class') classes.clear(); else delete attrs[a]; },
      hasAttribute: a => a in attrs,
      classList: {
        contains: c => classes.has(c), add: c => classes.add(c), remove: c => classes.delete(c),
        toggle(c, on) { if (on === undefined ? !classes.has(c) : on) classes.add(c); else classes.delete(c); return classes.has(c); },
      },
      addEventListener(type, fn) { (events[type] ||= []).push(fn); },
      fire(type, e = {}) {
        let stopped = false, prevented = false;
        const ev = { type, target: el, detail: 1, pointerType: 'mouse', preventDefault() { prevented = true; ev.defaultPrevented = true; },
                     stopPropagation() { stopped = true; }, defaultPrevented: false, ...e };
        for (const fn of events[type] || []) fn(ev);
        // clicks and keys bubble
        if (!stopped && (type === 'click' || type === 'keydown') && el.parentNode && el.parentNode.fire && !e.noBubble) {
          el.parentNode.fire(type, { ...e, target: ev.target, _bubbled: true });
        }
        return { prevented, ev };
      },
      all(predicate) { const out = []; const walk = x => { if (x.classList && predicate(x)) out.push(x); (x.children || []).forEach(walk); }; this.children.forEach(walk); return out; },
      querySelectorAll(sel) { return this.all(x => matches(x, sel)); },
      querySelector(sel) { return this.querySelectorAll(sel)[0] || null; },
      closest(sel) { let x = this; while (x) { if (x.classList && matches(x, sel)) return x; x = x.parentNode; } return null; },
      contains(x) { while (x) { if (x === this) return true; x = x.parentNode; } return false; },
      focus() { doc.activeElement = this; },
      scrollBy() {},
      animate(frames, opts) { animations.push({ el: this, frames, opts }); const a = { cancel() {} }; return a; },
      getBoundingClientRect() {
        if (this._rect) return this._rect;
        if (doc.columnTitleTop != null && classes.has('sc__title')) {
          const top = doc.columnTitleTop;
          return { top, bottom: top + 28, left: 0, right: 327, width: 327, height: 28 };
        }
        // The drawing's area is as wide as the test asks.
        if (doc.areaWidth && classes.has('sm-area')) {
          const hh = doc.areaHeight || 900;
          return { left: 0, top: 120, width: doc.areaWidth, height: hh, right: doc.areaWidth, bottom: 120 + hh, x: 0, y: 120 };
        }
        const left = 40 + (n % 11) * 7, top = n * 9, width = 180, height = 22;
        return { left, top, width, height, right: left + width, bottom: top + height, x: left, y: top };
      },
    };
    return el;
  }
  Object.assign(doc, { node, animations });
  return doc;
}

/* ---- Mounting -------------------------------------------------------------- */
// `page`: the drawing on its own page with an address, in the column layout
// it had before the explorer. `explorer`: docs/system-map.html as the builder
// emits it since 5 October 2026 (a [data-explorer] main holding the panel and
// the stage, the frame's controls in the stage's top right, its key in the
// bottom left). `expand`: the landing's ways into the full map.
async function mount({ scene = liveScene(), doctrine, reduce = false, hash = '', page = false, column = true, inert = false,
                       areaWidth = 820, areaHeight = 900, innerHeight = 900, headerBottom = 0, columnTitleTop = null,
                       explorer = false, visible = false } = {}) {
  if (doctrine === undefined) doctrine = doctrineFor(scene);
  if (explorer) page = true;
  const dom = makeDom();
  dom.areaWidth = areaWidth;
  dom.areaHeight = areaHeight;
  dom.columnTitleTop = columnTitleTop;
  const { node } = dom;
  const section = node(explorer ? 'main' : 'section');
  const dispatched = [];
  if (explorer) {
    section.className = 'explorer system-explorer';
    section.setAttribute('data-explorer', 'system');
    section.dispatchEvent = ev => { dispatched.push(ev.type); section.fire(ev.type, { detail: ev.detail }); return true; };
  } else section.setAttribute('data-atlas-slide', 'system');
  if (page) section.setAttribute('data-system-page', '');
  section.inert = inert;
  let host, about = null, headEl = null;
  if (explorer) {
    const panelEl = section.appendChild(node('aside'));
    panelEl.className = 'explorer__panel';
    headEl = panelEl.appendChild(node('div'));
    headEl.className = 'explorer__head';
    const title = headEl.appendChild(node('h1'));
    title.className = 'explorer__title';
    title.textContent = 'The system map';
    host = panelEl.appendChild(node('div'));
    host.className = 'explorer__body';
    host.setAttribute('data-system-panel', '');
  } else {
    host = section.appendChild(node('div'));
    host.className = 'home-split__text';
    host.appendChild(node('h2'));
  }
  const listParent = explorer ? host.appendChild(node('section')) : host;
  if (explorer) {
    about = host.appendChild(node('section'));
    about.className = 'system-explorer__section system-explorer__about';
  }
  const list = listParent.appendChild(node('ol'));
  list.className = 'home-families';
  const areas = scene.scene.nodes.filter(n => n.kind === 'area');
  const rows = areas.map(a => {
    const li = list.appendChild(node('li'));
    li.className = 'home-family';
    li.setAttribute('data-system-family', a.id);
    const link = li.appendChild(node('a'));
    link.setAttribute('href', `docs/${a.id}.html`);
    const name = link.appendChild(node('span'));
    name.className = 'home-family__name';
    name.textContent = a.label;
    return li;
  });
  if (!column) section.removeChild(host);
  const stage = section.appendChild(node(explorer ? 'section' : 'figure'));
  stage.className = explorer ? 'explorer__stage' : 'home-split__figure home-system';
  stage.setAttribute('data-system-stage', '');
  stage._rect = { left: 600, top: 0, width: 800, height: 640, right: 1400, bottom: 640 };
  const holder = stage.appendChild(node('div'));
  holder.className = 'sm-mount';
  holder.setAttribute('data-system-src', page ? 'architecture-graph-scene.json' : 'docs/architecture-graph-scene.json');
  holder.setAttribute('data-system-doctrine', page ? 'doctrine-manifest.json' : 'docs/doctrine-manifest.json');
  holder.setAttribute('data-system-base', page ? '' : 'docs/');
  const fallback = holder.appendChild(node('p'));
  fallback.className = 'sm-fallback';
  let keySlot;
  if (explorer) {
    // The frame's controls in the stage's top right (the drawing's area
    // stands at left 0, top 120 in the fake layout).
    const tools = stage.appendChild(node('div'));
    tools.className = 'explorer__tools';
    tools._rect = { left: areaWidth - 254, right: areaWidth - 14, top: 134, bottom: 170, width: 240, height: 36 };
    const legend = stage.appendChild(node('div'));
    legend.className = 'explorer__legend';
    keySlot = legend.appendChild(node('span'));
  } else {
    const cap = stage.appendChild(node('figcaption'));
    keySlot = cap.appendChild(node('span'));
  }
  keySlot.className = 'sm-keyslot';
  // The landing's way into the full map, kept on the drawing's choice.
  const expandLinks = [node('a')];
  expandLinks[0].className = 'home-atlas__expand';
  expandLinks[0].setAttribute('data-system-expand', '');
  expandLinks[0].setAttribute('href', 'docs/system-map.html');

  const docListeners = {};
  const document = Object.assign(dom, {
    readyState: 'complete', hidden: false, activeElement: null, visibilityState: visible ? 'visible' : undefined,
    documentElement: node('html'),
    createElement: tag => node(tag),
    createElementNS: (ns, tag) => node(tag),
    createTextNode: text => ({ textContent: String(text), children: [], parentNode: null }),
    querySelectorAll: s => (s === '[data-system-stage]' ? [stage] : /data-system-expand/.test(s) && !page ? expandLinks : []),
    querySelector: s => s === '.docs-topbar' && headerBottom ? { getBoundingClientRect: () => ({ bottom: headerBottom }) } : null,
    addEventListener(type, fn) { (docListeners[type] ||= []).push(fn); },
    fire(type, e = {}) {
      let prevented = false;
      const ev = { type, target: e.target || null, defaultPrevented: false, preventDefault() { prevented = true; this.defaultPrevented = true; }, ...e };
      for (const fn of docListeners[type] || []) fn(ev);
      return prevented;
    },
  });
  const history = [], frames = [], scrolls = [];
  const window = {
    location: { hash, pathname: page ? '/docs/system-map.html' : '/', search: '' },
    history: {
      state: null,
      pushState(st, t, url) { history.push(['push', url]); window.location.hash = url.startsWith('#') ? url : ''; },
      replaceState(st, t, url) { history.push(['replace', url]); window.location.hash = url.startsWith('#') ? url : ''; },
      back() { history.push(['back']); },
    },
    innerHeight, pageYOffset: 0,
    requestAnimationFrame(fn) { frames.push(fn); return frames.length; },
    scrollBy(opts) { scrolls.push(opts); dom.columnTitleTop -= opts.top; },
    matchMedia: q => ({ matches: /reduce/.test(q) ? reduce : /hover/.test(q), addEventListener() {} }),
    getComputedStyle: () => ({ fontSize: '16px', getPropertyValue: () => '' }),
    addEventListener() {},
  };
  const requests = [];
  vm.runInNewContext(source, {
    window, document, Promise, Math, JSON, Object, Array, Date, Number, String, isFinite,
    fetch: async (url, opts) => {
      requests.push({ url, opts });
      if (/doctrine-manifest\.json/.test(url)) {
        return doctrine ? { ok: true, json: async () => clone(doctrine) } : { ok: false, status: 404, json: async () => ({}) };
      }
      return { ok: true, json: async () => scene };
    },
    setTimeout: fn => { fn(); return 1; }, clearTimeout() {},
    CustomEvent: class { constructor(type, init) { this.type = type; this.detail = init && init.detail; } },
  });
  for (let k = 0; k < 8; k++) await new Promise(r => setImmediate(r));
  const map = window.PlectisSystemMap;
  const root = holder.querySelector('.sm');
  const panel = () => host.querySelector('.sc__page');
  const textOf = scope => (scope ? scope.textContent : '');
  const wires = () => (root ? root.querySelectorAll('.sm-wire') : []);
  const press = el => el.fire('click', { detail: 0 });
  const click = el => el.fire('click', { detail: 1 });
  const key = k => document.fire('keydown', { key: k });
  return { map, window, document, section, host, stage, holder, root, rows, list, keySlot, requests, history,
           about, headEl, expandLinks, dispatched,
           scrolls, flushFrames() { frames.splice(0).forEach(fn => fn()); },
           animations: dom.animations, panel, textOf, wires, press, click, key, core: window.PlectisSystemMapCore };
}
const counts = scene => {
  const fam = famOf(scene), links = declared(scene).filter(e => fam[e.source] && fam[e.target] && e.source !== e.target);
  const seen = new Set(), uniq = links.filter(e => { const k = e.source + '>' + e.target; if (seen.has(k)) return false; seen.add(k); return true; });
  const pairs = new Set(uniq.filter(e => fam[e.source] !== fam[e.target]).map(e => [fam[e.source], fam[e.target]].sort().join('|')));
  return { links: uniq, pairs, fam };
};
const visibleText = scope => scope.all(n => !n.closest('[hidden]')).map(n => n._text).filter(Boolean).join(' \n ');

/* ---- Helpers over the fixtures ---------------------------------------------- */
const keyOf = el => el.getAttribute('data-sm-key');
const keys = list => list.map(keyOf);
const ruleKey = el => (el.getAttribute('data-sm-key') || '').slice(5);
function busiest(scene) {
  const c = counts(scene), tally = {};
  c.links.forEach(e => { tally[e.source] = (tally[e.source] || 0) + 1; tally[e.target] = (tally[e.target] || 0) + 1; });
  return Object.entries(tally).sort((x, y) => y[1] - x[1] || (x[0] < y[0] ? -1 : 1))[0][0];
}
function isolated(scene) {
  const c = counts(scene), touched = new Set(c.links.flatMap(e => [e.source, e.target]));
  return compNodes(scene).map(n => n.id).find(id => !touched.has(id)) || null;
}
// The doctrine's relations, as the drawing must have them: rests-on and
// threatens, one span each.
function spansOf(doctrine) {
  return [...doctrine.principles.flatMap(p => p.rests_on.map(a => p.id + '>' + a)),
          ...doctrine.anti_principles.flatMap(f => f.guards.map(a => f.id + '>' + a))].sort();
}
const spanKey = w => w.getAttribute('data-from').slice(5) + '>' + w.getAttribute('data-to').slice(5);
/* ---- The data and its orders ------------------------------------------------ */
test('the scene is read into families, components and links, every link kept once', async () => {
  const page = await mount();
  const s = page.map.snapshot();
  const scene = liveScene(), c = counts(scene);
  assert.equal(s.ready, true);
  assert.equal(s.counts.components, compNodes(scene).length);
  assert.equal(s.counts.families, new Set(Object.values(c.fam)).size);
  assert.equal(s.counts.links, c.links.length);
  assert.equal(s.counts.bands, c.pairs.size, 'every pair of families with a link between them is counted once');
  assert.equal(s.ring.order.length, s.counts.families);
});

test('the families go round the ring in the order whose links between them cross least', async () => {
  const { core } = await mount();
  const model = core.readScene(liveScene(), 'docs/');
  const a = core.familyRing(model), b = core.familyRing(model);
  assert.deepEqual(plain(a.order), plain(b.order), 'deterministic');
  const n = model.families.length;
  assert.equal(a.order[0], 0, 'the first published family stands at the top');
  assert.deepEqual(plain(a.order).slice().sort((x, y) => x - y), [...Array(n).keys()]);
  // Two families' links cross another two's when their arcs interleave.
  const crossings = order => {
    const slot = []; order.forEach((f, i) => { slot[f] = i; });
    const arcs = model.pairs.map(p => { const x = slot[p.a], y = slot[p.b], d = (y - x + n) % n; return d <= n - d ? [x, d] : [y, n - d]; });
    let c = 0;
    arcs.forEach((p, i) => arcs.forEach((q, j) => {
      if (j <= i) return;
      const ends = [p[0], (p[0] + p[1]) % n], other = [q[0], (q[0] + q[1]) % n];
      if (ends.some(e => other.includes(e))) return;
      const inside = v => { const d = (v - p[0] + n) % n; return d > 0 && d < p[1]; };
      if (inside(other[0]) !== inside(other[1])) c++;
    }));
    return c;
  };
  assert.equal(crossings(plain(a.order)), a.crossings);
  // Every other order with the first family first crosses at least as much.
  const rest = [...Array(n - 1).keys()].map(k => k + 1);
  const perms = list => (list.length < 2 ? [list] : list.flatMap((x, i) => perms([...list.slice(0, i), ...list.slice(i + 1)]).map(p => [x, ...p])));
  perms(rest).forEach(p => assert.ok(crossings([0, ...p]) >= a.crossings));
});

test('the doctrine reads in, each relation derived from one side so the two always agree', async () => {
  const { core } = await mount();
  const scene = liveScene(), doctrine = doctrineFor(scene);
  const model = core.readScene(scene, 'docs/');
  const D = core.readDoctrine(doctrine, model, 'docs/');
  assert.equal(D.axioms.length, 12);
  assert.equal(D.principles.length, 20);
  assert.equal(D.failures.length, 17);
  D.axioms.forEach(a => D.rules[a].grounds.forEach(p => assert.ok(D.rules[p].restsOn.includes(a))));
  D.axioms.forEach(a => D.rules[a].threatenedBy.forEach(f => assert.ok(D.rules[f].guards.includes(a))));
  D.principles.forEach(p => D.rules[p].restsOn.forEach(a => assert.ok(D.rules[a].grounds.includes(p))));
});

test('a relation may carry a verdict once checked against the code, and the verdict is kept beside it', async () => {
  const { core } = await mount();
  const scene = liveScene();
  const edge = declared(scene)[0];
  edge.verdict = 'verified';
  const model = core.readScene(scene, 'docs/');
  const a = model.comps.findIndex(c => c.id === edge.source), b = model.comps.findIndex(c => c.id === edge.target);
  assert.equal(model.verdicts[a + '>' + b], 'verified');
  const doctrine = doctrineFor(scene);
  doctrine.components[0].governed_by = [{ id: 'P-2', verdict: 'declared only' }];
  const D = core.readDoctrine(doctrine, model, 'docs/');
  const ci = model.comps.findIndex(c => c.id === doctrine.components[0].id);
  assert.deepEqual(plain(D.comp[ci].gov), ['P-2']);
  assert.equal(D.verdicts['governed_by:' + doctrine.components[0].id + '>P-2'], 'declared only');
});

test('authored prose is trimmed to its opening sentences and stops before a file name or a dash', async () => {
  const { core } = await mount();
  assert.equal(core.trimProse('It reads its inputs. It loads helper_module.py first. It stops.', 400), 'It reads its inputs.');
  assert.equal(core.trimProse('One — two. Three.', 400), null);
  assert.equal(core.trimProse('A short one. A second one that is still short. A third.', 30), 'A short one.');
});

/* ---- The system ------------------------------------------------------------- */
test('the system: every component on the rim, the families named round it, the doctrine as a necklace at the centre', async () => {
  const scene = liveScene(), doctrine = doctrineFor(scene);
  const page = await mount({ scene, doctrine });
  const s = page.map.snapshot();
  assert.equal(s.view, 'system');
  assert.deepEqual(plain(s.crumbs), ['System']);
  assert.match(s.caption, /^\d+ components round the rim in seven families, the doctrine at the centre\. Select any of them to light what it touches\.$/);
  const r = page.root;
  assert.equal(r.querySelectorAll('.sm-node--comp').length, s.counts.components);
  assert.equal(r.querySelectorAll('.sm-node--fam').length, s.counts.families);
  assert.equal(r.querySelectorAll('.sm-node--rule').length, 12 + 20 + 17);
  assert.equal(r.querySelectorAll('.sm-node--hub').length, 12);
  const single = [...doctrine.principles.filter(p => p.rests_on.length === 1), ...doctrine.anti_principles.filter(f => f.guards.length === 1)];
  assert.equal(r.querySelectorAll('.sm-node--sat').length, single.length);
  assert.equal(r.querySelectorAll('.sm-node--bridge').length, 37 - single.length);
  // The doctrine's own relations, each its own line, and nothing else at rest.
  assert.deepEqual(r.querySelectorAll('.sm-span').map(spanKey).sort(), spansOf(doctrine));
  assert.equal(r.querySelectorAll('.sm-route').length + r.querySelectorAll('.sm-rline').length, 0, 'nothing is lit at rest');
  assert.equal(r.querySelectorAll('.sm-lane').length, 0, 'no rings of routes round the core');
  assert.equal(r.querySelectorAll('.sm-necklace').length, 1, 'one faint orbit under the necklace');
  // The rim: a tick for each component, a bar where its page cites rules,
  // a crossbar where a rule's card names it.
  assert.equal(r.querySelectorAll('.sm-tick').filter(t => t.getAttribute('data-sm-tick')).length, s.counts.components);
  const citing = doctrine.components.filter(c => c.governed_by.length + c.abides_by.length > 0).length;
  assert.equal(r.querySelectorAll('.sm-bar').length, citing);
  const named = new Set([...doctrine.axioms, ...doctrine.principles, ...doctrine.anti_principles].flatMap(x => x.enforced_in));
  assert.equal(r.querySelectorAll('.sm-cap').length, named.size);
  assert.doesNotMatch(visibleText(r), UNPLAIN);
});

test('the key is one row in plain words, and every other mark is named behind its disclosure', async () => {
  const page = await mount();
  const rows = () => page.keySlot.querySelectorAll('.sm-key__row');
  assert.equal(rows().length, 1);
  const text = page.textOf(page.keySlot);
  ['Listed as related', 'Cited by its paper module', 'Axiom', 'Principle', 'Failure mode'].forEach(w => assert.match(text, new RegExp(w)));
  assert.doesNotMatch(text, /Named links|Rules cited|works with/);
  const more = page.keySlot.querySelector('.sm-key__more');
  assert.equal(more.getAttribute('aria-expanded'), 'false');
  page.press(more);
  assert.equal(rows().length, 2);
  const all = page.textOf(page.keySlot);
  ['Runs a real tool', 'One step for each rule its paper module cites', 'A rule’s card says it is enforced here', 'Rests on', 'Threatens',
   'Where a red line and an azure line cross, one passes over the other']
    .forEach(w => assert.match(all, new RegExp(w)));
  assert.equal(page.keySlot.querySelector('.sm-key__more').getAttribute('aria-expanded'), 'true');
});

test('the column’s families follow the ring’s order and work the drawing; a plain click opens the family', async () => {
  const page = await mount();
  const s = page.map.snapshot();
  const order = page.list.querySelectorAll('.home-family').map(li => li.getAttribute('data-system-family'));
  assert.deepEqual(order, plain(s.ring.order));
  const first = page.list.querySelector('.home-family');
  first.fire('pointerenter');
  assert.equal(page.map.snapshot().hover, 'fam:' + s.ring.order[0].slice(5));
  first.fire('pointerleave');
  const link = first.querySelector('a');
  assert.equal(link.fire('click', { metaKey: true, noBubble: true }).prevented, false, 'a modified click keeps the family page');
  assert.equal(page.map.snapshot().view, 'system');
  assert.equal(link.fire('click', { noBubble: true }).prevented, true);
  assert.equal(page.map.snapshot().view, 'family');
});

/* ---- A family ----------------------------------------------------------------- */
test('a family lights its members and every link that touches it, each line from the family outward', async () => {
  const scene = liveScene(), c = counts(scene);
  const page = await mount({ scene });
  const fam = 'formal_math_and_proof';
  page.map.select('area:' + fam);
  const s = page.map.snapshot();
  assert.equal(s.view, 'family');
  assert.deepEqual(plain(s.crumbs).slice(0, 1), ['System']);
  const touching = c.links.filter(e => c.fam[e.source] === fam || c.fam[e.target] === fam);
  assert.equal(s.lit.routes, touching.length);
  const routes = page.root.querySelectorAll('.sm-route.sm-wire');
  assert.equal(routes.length, touching.length);
  routes.forEach(w => assert.equal(c.fam[w.getAttribute('data-from').slice(5)], fam, 'each lit line runs from the family out'));
  const members = compNodes(scene).filter(n => c.fam[n.id] === fam);
  assert.equal(page.root.querySelectorAll('.sm-node--comp.is-member').length, members.length);
  // Its own name is lit where it stands; a closer look names the family by
  // its components instead, and lights its scale on the rim.
  const own = page.root.querySelector('.sm-node--fam[data-sm-key="fam:' + fam + '"]');
  if (own) assert.ok(own.classList.contains('is-self'), 'its own name is lit');
  else assert.ok(page.root.querySelector('.sm-scale__sector.is-self[data-fam="' + fam + '"]'), 'its scale is lit');
  assert.equal(page.root.querySelectorAll('.sm-scale__sector.is-self').length, 1, 'one family’s scale is lit');
  const partners = new Set(touching.map(e => c.fam[e.source] === fam ? c.fam[e.target] : c.fam[e.source]).filter(f => f !== fam));
  const named = page.root.querySelectorAll('.sm-node--fam').filter(n => partners.has(n.getAttribute('data-sm-key').slice(4)));
  assert.ok(named.every(n => n.classList.contains('is-lit')), 'the families it links with are lit where they are named');
  assert.equal(page.root.querySelectorAll('.sm-node--fam.is-lit').length, named.length, 'and no other');
  assert.equal(page.panel().querySelector('.sc__title').textContent, s.crumbs[1]);
  assert.match(page.textOf(page.panel()), new RegExp('Its components · ' + members.length));
  assert.match(s.caption, /^Its \w+ components and their listed relations, inside the family and out to the others\.$/);
  page.root.querySelectorAll('.sm-route').forEach(w => assert.match(w.getAttribute('d'), /Z/, 'a fibre is a filled outline'));
});

/* ---- A component -------------------------------------------------------------- */
test('a component lights its links, the rules its paper module cites and the axioms they rest on, and never a line to an axiom a principle already reaches', async () => {
  const scene = liveScene(), doctrine = doctrineFor(scene), c = counts(scene);
  const P = Object.fromEntries(doctrine.principles.map(p => [p.id, p]));
  const row = doctrine.components.find(r => {
    const reached = new Set(r.governed_by.flatMap(p => P[p].rests_on));
    return r.abides_by.some(a => !reached.has(a)) && c.links.some(e => e.source === r.id || e.target === r.id);
  });
  const page = await mount({ scene, doctrine });
  page.map.select(row.id);
  const s = page.map.snapshot();
  assert.equal(s.view, 'component');
  assert.equal(s.crumbs.length, 3);
  const reached = new Set(row.governed_by.flatMap(p => P[p].rests_on));
  const direct = row.abides_by.filter(a => !reached.has(a));
  const lines = page.root.querySelectorAll('.sm-rline');
  lines.forEach(w => assert.equal(w.getAttribute('data-from'), 'comp:' + row.id));
  assert.deepEqual(lines.map(w => w.getAttribute('data-to').slice(5)).sort(), [...new Set([...row.governed_by, ...direct])].sort());
  lines.forEach(w => assert.ok(!reached.has(w.getAttribute('data-to').slice(5)) || /^P-/.test(w.getAttribute('data-to').slice(5)),
    'no line from a component to an axiom one of its principles rests on'));
  // The principles' own relations to their axioms are what light the axioms.
  const lit = page.root.querySelectorAll('.sm-span.is-lit').map(spanKey).sort();
  assert.deepEqual(lit, [...new Set(row.governed_by.flatMap(p => P[p].rests_on.map(a => p + '>' + a)))].sort());
  // Its links, each a line from it.
  const touching = c.links.filter(e => e.source === row.id || e.target === row.id);
  const routes = page.root.querySelectorAll('.sm-route.sm-wire');
  assert.equal(routes.length, touching.length);
  routes.forEach(w => assert.equal(w.getAttribute('data-from'), 'comp:' + row.id));
  // Where a rule is shown holding here its glyph is framed, as the component
  // is framed in that rule's own view (the chosen component first); no line
  // is drawn to a rule its paper module does not cite.
  const held = [...doctrine.axioms, ...doctrine.principles, ...doctrine.anti_principles]
    .filter(r => (r.enforced_in || []).includes(row.id)).map(r => 'rule:' + r.id);
  assert.equal(plain(s.lit.reticles)[0], 'comp:' + row.id);
  assert.deepEqual(plain(s.lit.reticles).sort(), ['comp:' + row.id, ...held].sort());
  const col = page.textOf(page.panel());
  assert.match(col, new RegExp('Its paper module cites · ' + new Set([...row.governed_by, ...row.abides_by]).size));
  assert.doesNotMatch(col, /Follows these principles|Cites these axioms|governed|abides/);
  // The published scene's links are the relations a component's record
  // lists: one list, no direction, and the column says they are not read from
  // the code.
  const others = new Set(touching.map(e => (e.source === row.id ? e.target : e.source)));
  assert.match(col, new RegExp('Listed as related · ' + others.size));
  assert.doesNotMatch(col, /Names · |Named by · /);
  assert.match(col, /Listed in a component’s own record, not read from the code\./);
  assert.match(s.caption, /^Red lines to the components listed as related, azure lines to the rules its paper module cites\.$/);
});

/* ---- Code connections --------------------------------------------------------- */
// The regenerated scene: a few dozen typed code connections in place of the
// hundreds of named links, the same shape otherwise.
function typedScene() {
  const json = liveScene();
  const kinds = ['runs', 'reads_results_of', 'checks_copies_of'];
  let k = 0;
  json.scene.edges = json.scene.edges.filter(e => {
    if ((e.relation || e.kind) !== 'declared_dependency_untyped') return true;
    if (k >= 36) return false;
    e.relation = kinds[k++ % 3];
    e.id = 'edge:wire:' + e.source.split(':').pop() + ':' + e.target.split(':').pop();
    e.evidence = { path: 'src/example.py', lines: [1, 9] };
    return true;
  });
  return json;
}
test('typed code connections: each kind in its own texture, named in plain words from either end, all shown quietly at rest', async () => {
  const scene = typedScene(), c = counts(liveScene());
  const page = await mount({ scene });
  const s = page.map.snapshot();
  assert.deepEqual(plain(s.counts.kinds), ['runs', 'reads', 'checks']);
  assert.equal(s.counts.links, 36);
  const key = page.textOf(page.keySlot);
  ['Runs', 'Reads saved results of', 'Checks the copied files of'].forEach(w => assert.match(key, new RegExp(w)));
  assert.doesNotMatch(key, /Named links/);
  // Few enough to show them all at rest, each in its kind's texture.
  // One fibre for each link (a ribbon's parting fibres among them); the
  // ribbons are drawn besides.
  const own = sel => page.root.querySelectorAll(sel).filter(f => !f.classList.contains('is-trunk'));
  assert.equal(own('.sm-fibre').length, 36);
  ['runs', 'reads', 'checks'].forEach(kind => assert.equal(own('.sm-fibre--' + kind).length, 12));
  assert.equal(page.root.querySelectorAll('.sm-fibre.is-trunk').length, s.ring.sheaves.length);
  // A component's column names each kind from its side.
  const edges = scene.scene.edges.filter(e => ['runs', 'reads_results_of', 'checks_copies_of'].includes(e.relation));
  const tally = {}; edges.forEach(e => { tally[e.source] = (tally[e.source] || 0) + 1; tally[e.target] = (tally[e.target] || 0) + 1; });
  const id = Object.entries(tally).sort((x, y) => y[1] - x[1] || (x[0] < y[0] ? -1 : 1))[0][0];
  page.map.select(id);
  // One list, each component named once with the ways the code connects
  // them, in the plain words from this component's side.
  const others = new Set(edges.filter(e => e.source === id || e.target === id).map(e => (e.source === id ? e.target : e.source)));
  const block = () => page.panel().querySelectorAll('.sc__block').find(b => /Code connections/.test(page.textOf(b)));
  assert.match(page.textOf(block()), new RegExp('Code connections · ' + others.size));
  if (block().querySelector('.sc__all')) page.press(block().querySelector('.sc__all'));
  const col = page.textOf(page.panel());
  const words = { runs: ['Runs', 'Run by'], reads_results_of: ['Reads results of', 'Results read by'], checks_copies_of: ['Checks copies of', 'Copies checked by'] };
  Object.entries(words).forEach(([rel, [out, inc]]) => {
    if (edges.some(e => e.relation === rel && e.source === id)) assert.match(col, new RegExp(out));
    if (edges.some(e => e.relation === rel && e.target === id)) assert.match(col, new RegExp(inc));
  });
  assert.equal(block().querySelectorAll('.sc__li').length, others.size);
  assert.match(col, page.panel().querySelector('.sc__code') ? /Each is derived from the code; Code opens the file that makes it\./ :
    /Each connection is derived from the code\./);
  assert.doesNotMatch(col + page.map.snapshot().caption, /works with|Listed as related/);
  assert.match(page.map.snapshot().caption, /^Red lines for its code connections, azure lines to the rules its paper module cites\.$/);
  page.root.querySelectorAll('.sm-route').forEach(w => assert.match(w.getAttribute('class'), /sm-route--(?:runs|reads|checks)/));
  // Its lit lines are woven with the rule lines and the pieces at rest that
  // are not lit (a ribbon is one strand, its parting fibres one each).
  const lit = page.map.snapshot();
  const resting = page.root.querySelectorAll('.sm-fibre').filter(f => !f.classList.contains('is-under')).length;
  assert.equal(lit.weave.strands, resting + page.root.querySelectorAll('.sm-route').length + lit.lit.lines, 'every fibre and every rule line goes into the weave');
  // A component with none says so plainly.
  const none = compNodes(scene).map(n => n.id).find(x => !tally[x]);
  page.map.select(none);
  assert.match(page.textOf(page.panel()), /No code connections\. Its code does not run, read or check another component, and no other component’s code runs, reads or checks it\./);
  assert.match(page.map.snapshot().caption, /^No code connections to other components; azure lines to the rules its paper module cites\.$/);
  assert.ok(c.links.length > 90, 'the published scene of named links is too many to show at rest');
});

test('choosing a linked component in the column opens it, and Back returns', async () => {
  const scene = liveScene();
  const page = await mount({ scene });
  const id = busiest(scene);
  page.map.select(id);
  const next = page.panel().querySelectorAll('.sc__item').find(b => (keyOf(b) || '').startsWith('comp:') && keyOf(b) !== 'comp:' + id);
  page.click(next);
  const s = page.map.snapshot();
  assert.equal('comp:' + s.component, keyOf(next));
  assert.match(s.back, /^Back to /);
  page.press(page.root.querySelector('.sm-back'));
  assert.equal(page.map.snapshot().component, id);
});

test('a component with no links says so, in the caption and the column', async () => {
  const scene = liveScene(), id = isolated(scene);
  if (!id) return;
  const page = await mount({ scene });
  page.map.select(id);
  // The published scene's relations are the ones a record lists, so a
  // component with none says that, in those terms.
  assert.match(page.map.snapshot().caption, /^Its record lists no related components; azure lines to the rules its paper module cites\.$/);
  assert.match(page.textOf(page.panel()), /Its record lists no related components\./);
  assert.equal(page.root.querySelectorAll('.sm-route').length, 0);
});

/* ---- The doctrine -------------------------------------------------------------- */
test('the doctrine view lights every rule and every span, and sends no line to the rim', async () => {
  const scene = liveScene(), doctrine = doctrineFor(scene);
  const page = await mount({ scene, doctrine });
  page.map.select('doctrine');
  const s = page.map.snapshot();
  assert.equal(s.view, 'doctrine');
  assert.deepEqual(plain(s.crumbs), ['System', 'The doctrine']);
  assert.equal(page.root.querySelectorAll('.sm-span.is-lit').length, spansOf(doctrine).length);
  assert.equal(page.root.querySelectorAll('.sm-rline').length, 0);
  assert.match(s.caption, /^Twelve axioms on a ring\. A rule tied to one axiom sits just outside it; a rule tied to several stands between them\.$/);
  const col = page.textOf(page.panel());
  assert.match(col, /Each rule’s doctrine card names the components where it is enforced\./);
});

test('a principle lights its axioms and a line out to every component whose paper module cites it; its card names where it is enforced', async () => {
  const scene = liveScene(), doctrine = doctrineFor(scene);
  const page = await mount({ scene, doctrine });
  page.map.select('doctrine:P-3');
  const s = page.map.snapshot();
  assert.equal(s.view, 'rule');
  assert.deepEqual(plain(s.crumbs), ['System', 'The doctrine', PRINCIPLES[2]]);
  const p = doctrine.principles[2];
  const citing = doctrine.components.filter(r => r.governed_by.includes('P-3')).map(r => r.id);
  const enforced = p.enforced_in;
  const lines = page.root.querySelectorAll('.sm-rline');
  lines.forEach(w => assert.equal(w.getAttribute('data-from'), 'rule:P-3', 'the light runs outward from the rule'));
  assert.deepEqual(lines.map(w => w.getAttribute('data-to').slice(5)).sort(), [...new Set([...citing, ...enforced])].sort());
  assert.deepEqual(page.root.querySelectorAll('.sm-span.is-lit').map(spanKey).sort(), p.rests_on.map(a => 'P-3>' + a).sort());
  assert.deepEqual(plain(s.lit.reticles).sort(), ['rule:P-3', ...enforced.map(id => 'comp:' + id)].sort());
  const col = page.textOf(page.panel());
  assert.match(col, /What concentrate trust in small checkers asks, in plain words\./);
  assert.match(col, /Rests on/);
  assert.match(col, /Enforced in/);
  assert.match(col, new RegExp('Cited by the paper modules of ' + citing.length + ' of ' + compNodes(scene).length + ' components'));
  const card = page.panel().querySelectorAll('a').find(a => /Read its doctrine card/.test(a.textContent));
  assert.equal(card.getAttribute('href'), 'docs/doctrine.html#dcard-p-3');
  assert.doesNotMatch(col, RULE_ID);
  assert.match(page.textOf(page.keySlot), /Enforced here, by its card/);
});

test('an axiom lights everything tied to it; a failure mode lights its axioms and only the components its card names', async () => {
  const scene = liveScene(), doctrine = doctrineFor(scene);
  const page = await mount({ scene, doctrine });
  page.map.select('doctrine:AX-5');
  const tied = spansOf(doctrine).filter(k => k.endsWith('>AX-5'));
  assert.deepEqual(page.root.querySelectorAll('.sm-span.is-lit').map(spanKey).sort(), tied);
  const citing = doctrine.components.filter(r => r.abides_by.includes('AX-5')).map(r => r.id);
  const lines = page.root.querySelectorAll('.sm-rline').map(w => w.getAttribute('data-to').slice(5));
  citing.forEach(id => assert.ok(lines.includes(id)));
  page.map.select('doctrine:AP-4');
  const f = doctrine.anti_principles[3];
  assert.deepEqual(page.root.querySelectorAll('.sm-span.is-lit').map(spanKey).sort(), f.guards.map(a => 'AP-4>' + a).sort());
  assert.deepEqual(page.root.querySelectorAll('.sm-rline').map(w => w.getAttribute('data-to').slice(5)).sort(), f.enforced_in.slice().sort());
  assert.match(page.map.snapshot().caption, /^Lit with the axioms it threatens and the components its card names as enforcing it\.$/);
});

/* ---- Words ---------------------------------------------------------------------- */
test('every word a reader sees is plain, and none claims a component’s code checks a rule', async () => {
  const scene = liveScene(), doctrine = doctrineFor(scene);
  const page = await mount({ scene, doctrine });
  const views = [null, 'area:formal_math_and_proof', 'area:entry_and_reveal', busiest(scene), isolated(scene), 'doctrine', 'doctrine:AX-5', 'doctrine:P-15', 'doctrine:AP-4'];
  for (const v of views) {
    page.map.select(v);
    const text = visibleText(page.root) + ' \n ' + visibleText(page.host) + ' \n ' + page.textOf(page.keySlot);
    assert.doesNotMatch(text, UNPLAIN, `view ${v}`);
    assert.doesNotMatch(text, /composition root naming/, 'the engineer’s note is never shown');
    assert.doesNotMatch(text, /helper_module/, 'a sentence with a file name is cut from the column');
    assert.doesNotMatch(text, /code checks/i, 'no claim that a component’s code checks a rule');
    assert.doesNotMatch(text, /Point at a component/, 'no filler box');
    assert.doesNotMatch(text, /works with\b|work together/, 'a link never claims two components work together');
  }
});

/* ---- Addresses, keys, motion ------------------------------------------------------ */
test('each page in the explorer is read from its top, and neither it nor the landing moves the window', async () => {
  const id = busiest(liveScene());
  const page = await mount({ explorer: true, hash: '#map=' + encodeURIComponent(id), headerBottom: 109.25, columnTitleTop: 59.48 });
  page.host.scrollTop = 640;
  page.map.select('doctrine:P-3');
  assert.equal(page.host.scrollTop, 0, 'a new choice opens its page at the top of the panel');
  page.host.scrollTop = 300;
  page.key('Escape');
  assert.equal(page.map.snapshot().view, 'doctrine');
  assert.equal(page.host.scrollTop, 0);
  page.host.scrollTop = 300;
  page.key('Escape');
  assert.equal(page.map.snapshot().view, 'system');
  assert.equal(page.host.scrollTop, 0, 'and the overview too');
  page.flushFrames();
  assert.equal(page.scrolls.length, 0, 'the window never scrolls: the panel does');
  const landing = await mount({ headerBottom: 109.25, columnTitleTop: 59.48 });
  landing.map.select(id); landing.flushFrames();
  assert.equal(landing.scrolls.length, 0);
});

test('on its own page the map follows #map= addresses and writes each view back', async () => {
  const scene = liveScene(), doctrine = doctrineFor(scene);
  const id = busiest(scene);
  let page = await mount({ scene, doctrine, explorer: true, hash: '#map=' + encodeURIComponent(id) });
  assert.equal(page.map.snapshot().component, id);
  assert.equal(page.map.snapshot().back, null, 'an arrival leaves nothing behind it');
  page.map.select('area:formal_math_and_proof');
  assert.deepEqual(page.history[page.history.length - 1], ['push', '#map=' + encodeURIComponent('family:formal_math_and_proof')]);
  page.map.select('doctrine:P-3');
  assert.deepEqual(page.history[page.history.length - 1], ['push', '#map=' + encodeURIComponent('doctrine:P-3')]);
  for (const [hash, want] of [['#map=family%3Aformal_math_and_proof', 'family'], ['#map=area%3Aentry_and_reveal', 'family'],
                              ['#map=doctrine', 'doctrine'], ['#map=doctrine%3AP-3', 'rule'], ['#map=' + encodeURIComponent(id), 'component']]) {
    page = await mount({ scene, doctrine, explorer: true, hash });
    assert.equal(page.map.snapshot().view, want, hash);
  }
});

test('Escape and the trail step back up a level; Back retraces a jump across the map', async () => {
  const scene = liveScene();
  const page = await mount({ scene });
  page.map.select(busiest(scene));
  page.key('Escape');
  assert.equal(page.map.snapshot().view, 'family');
  page.key('Escape');
  assert.equal(page.map.snapshot().view, 'system');
  assert.equal(page.key('Escape'), false, 'at the top Escape is left for others');
  page.map.select('doctrine:P-3');
  page.press(page.root.querySelectorAll('.sm-crumbs__go')[1]);
  assert.equal(page.map.snapshot().view, 'doctrine');
});

test('the keyboard: Enter on a family name opens it, Escape returns the focus to it, and the arrows walk round the rim', async () => {
  const page = await mount();
  const fam = page.root.querySelector('.sm-node--fam');
  fam.fire('keydown', { key: 'Enter', target: fam });
  assert.equal(page.map.snapshot().view, 'family');
  page.key('Escape');
  assert.equal(page.map.snapshot().view, 'system');
  assert.equal(keyOf(page.document.activeElement), keyOf(fam));
  const comps = page.root.querySelectorAll('.sm-node--comp');
  const first = comps[0];
  first.fire('keydown', { key: 'ArrowRight', target: first });
  const now = page.document.activeElement;
  assert.ok(now && now.classList.contains('sm-node--comp') && now !== first, 'the next component round the rim takes the focus');
  assert.equal(now.getAttribute('tabindex'), '0');
  now.fire('keydown', { key: 'ArrowUp', target: now });
  assert.ok(page.document.activeElement.classList.contains('sm-node--fam'), 'up from a component is its family');
});

test('Escape is ignored while the system slide is out of view', async () => {
  const page = await mount({ inert: true });
  page.map.select('area:formal_math_and_proof');
  page.key('Escape');
  assert.equal(page.map.snapshot().view, 'family');
});

test('reduced motion lands every change at once; otherwise the map assembles once and every motion is short', async () => {
  const scene = liveScene();
  const still = await mount({ scene, reduce: true });
  still.map.select('area:formal_math_and_proof');
  still.map.select(busiest(scene));
  still.map.select('doctrine:P-3');
  assert.equal(still.animations.length, 0);
  // A scene of code connections draws its fibres at rest, so its first
  // sight has lines to run out.
  const moving = await mount({ scene: codeScene() });
  const opening = moving.animations.length;
  // The rim and the glyphs arrive in place with the slide; the first sight
  // runs the lines out, once, and nothing pops in.
  assert.ok(opening > 20, 'the first sight runs the lines out');
  assert.equal(moving.animations.filter(a => JSON.stringify(a.frames).includes('scale(0.35)')).length, 0, 'no mark pops in');
  moving.map.select(busiest(scene));
  assert.ok(moving.animations.length > opening, 'a choice moves');
  moving.animations.forEach(a => assert.ok(a.opts.duration <= 900 && (a.opts.delay || 0) <= 1300, 'each motion is short'));
  moving.map.select(null);
  const before = moving.animations.length;
  moving.document.fire('plectis:atlas', { detail: { view: 'system', previous: 'mathematics', phase: 'end' } });
  assert.equal(moving.animations.length, before, 'the opening plays once');
});

test('the scene and the doctrine are each fetched once, and the API answers before they arrive', async () => {
  const page = await mount();
  assert.equal(page.requests.filter(r => /architecture-graph-scene/.test(r.url)).length, 1);
  assert.equal(page.requests.filter(r => /doctrine-manifest/.test(r.url)).length, 1);
  assert.equal(page.requests[0].opts.cache, 'no-cache');
  assert.equal(page.map.snapshot().doctrine, true);
});

test('without the doctrine the components still work, and the doctrine waits for it', async () => {
  const scene = liveScene();
  const page = await mount({ scene, doctrine: null });
  page.map.select(busiest(scene));
  const s = page.map.snapshot();
  assert.equal(s.doctrine, false);
  assert.equal(s.view, 'component');
  assert.equal(page.root.querySelectorAll('.sm-node--rule').length, 0);
  assert.equal(page.root.querySelectorAll('.sm-rline').length, 0);
  page.map.select('doctrine');
  assert.equal(page.map.snapshot().view, 'component', 'no doctrine view without the doctrine');
});

test('a stale scene without details still draws its families and components', async () => {
  const page = await mount({ scene: staleScene(), doctrine: null });
  const s = page.map.snapshot();
  assert.equal(s.ready, true);
  assert.equal(page.root.querySelectorAll('.sm-node--fam').length, s.counts.families);
  assert.equal(page.root.querySelectorAll('.sm-node--comp').length, s.counts.components);
});

test('bad rows are dropped and the rest is drawn', async () => {
  const scene = liveScene();
  scene.scene.nodes.push(clone(scene.scene.nodes[0]));
  scene.scene.edges.push({ id: 'x', source: 'component:nope', target: compNodes(scene)[0].id, relation: 'declared_dependency_untyped' });
  scene.scene.edges.push(clone(declared(scene)[0]));
  scene.scene.edges.push('not an edge');
  const page = await mount({ scene, doctrine: null });
  const s = page.map.snapshot();
  assert.equal(s.ready, true);
  assert.ok(s.counts.dropped >= 3);
  assert.equal(s.counts.links, counts(liveScene()).links.length);
});

/* ---- Opening a page, and the camera (Will, 5 Oct) ------------------------------- */
test('a second click on what is chosen, or a double click, opens its page; Enter does it from the keyboard', async () => {
  const scene = liveScene(), doctrine = doctrineFor(scene);
  const page = await mount({ scene, doctrine, reduce: true });
  const id = busiest(scene), node = () => page.root.querySelector('.sm-node--comp[data-sm-key="comp:' + id + '"]');
  const slug = id.replace(/^[a-z_]+:/, '').replace(/_/g, '-');
  page.click(node());
  assert.equal(page.map.snapshot().view, 'component', 'a first click chooses');
  assert.equal(page.window.location.href, undefined, 'and stays on the map');
  page.click(node());
  assert.equal(page.window.location.href, 'docs/component-' + slug + '.html', 'a second click opens its page');
  // A double click on a mark not yet chosen: the first click chooses it, the second opens it.
  const fresh = await mount({ scene, doctrine, reduce: true });
  const rule = fresh.root.querySelector('.sm-node--rule[data-sm-key="rule:P-3"]');
  rule.fire('click', { detail: 1 });
  assert.equal(fresh.map.snapshot().view, 'rule');
  rule.fire('click', { detail: 2 });
  assert.equal(fresh.window.location.href, 'docs/doctrine.html#dcard-p-3', 'a rule opens at its card');
  // Enter on what is already chosen opens it too.
  const keyed = await mount({ scene, doctrine, reduce: true });
  keyed.map.select('doctrine');
  const centre = keyed.root.querySelector('[data-sm-key="doctrine"]');
  centre.fire('keydown', { key: 'Enter', target: centre });
  assert.equal(keyed.window.location.href, 'docs/doctrine.html', 'the doctrine opens its page');
});

test('a family, a component and the doctrine are looked at closely; a rule and the whole system from the usual distance', async () => {
  const scene = liveScene(), doctrine = doctrineFor(scene);
  const page = await mount({ scene, doctrine, areaWidth: 820 });
  assert.equal(page.map.snapshot().camera, null, 'the whole system rests');
  page.map.select('doctrine');
  const core = page.map.snapshot().camera;
  assert.ok(core && core.k > 1.2, 'the doctrine fills the drawing');
  page.map.select('doctrine:P-3');
  assert.equal(page.map.snapshot().camera, null, 'a rule reaches round the whole ring');
  page.map.select('area:formal_math_and_proof');
  const fam = page.map.snapshot().camera;
  if (fam) {
    assert.equal(fam.names, 'area:formal_math_and_proof', 'a family looked at closely names its components');
    const members = compNodes(scene).filter(n => n.parent_cluster_id === 'cluster:formal_math_and_proof').length;
    assert.equal(page.root.querySelectorAll('.sm-rimname--cam').length, members);
  }
  // Every view drawn under a camera keeps the drawing's box and never cuts a word: a
  // family's name is set only where it stands whole.
  page.map.select(null);
  assert.equal(page.map.snapshot().camera, null);
  assert.equal(page.root.querySelectorAll('svg.sm-ring').length, 1, 'once settled, one drawing');
});

test('what is pointed at is named beside its mark and read out in a place of its own; the chosen mark says how to open it', async () => {
  // A Type B review (6 October 2026) found the floating tip covering the
  // small drawing it described: the name now stands beside the mark and
  // the sentence goes in the card's own sentence box.
  const scene = liveScene(), doctrine = doctrineFor(scene);
  const page = await mount({ scene, doctrine, reduce: true });
  assert.equal(page.root.querySelector('.sm-tip'), null, 'no floating tip');
  const out = page.root.querySelector('.sm-readout');
  assert.ok(out && out.hidden, 'nothing is read out at rest');
  const fam = page.root.querySelector('.sm-node--fam');
  fam.fire('pointerenter', { pointerType: 'mouse' });
  assert.equal(out.hidden, false);
  assert.match(page.textOf(out), / components?/, 'a family is read out with its count');
  assert.ok(page.root.querySelector('.sm-caption').classList.contains('is-read-over'), 'over the card’s own sentence');
  fam.fire('pointerleave', { pointerType: 'mouse' });
  assert.equal(out.hidden, true);
  assert.ok(!page.root.querySelector('.sm-caption').classList.contains('is-read-over'), 'and the sentence comes back');
  // A rule pointed at is read out, and named beside its glyph in its ink
  // wherever its name stands clear (at the landing's smallest size, nearly
  // all of them); leaving it takes the name away.
  const rules = doctrine.axioms.concat(doctrine.principles, doctrine.anti_principles);
  const glyphs = page.root.querySelectorAll('.sm-node--rule');
  let named = 0;
  glyphs.forEach(glyph => {
    const title = rules.find(r => r.id === glyph.getAttribute('data-sm-key').slice(5)).title;
    glyph.fire('pointerenter', { pointerType: 'mouse' });
    assert.ok(page.textOf(out).includes(title), 'read out: ' + title);
    const set = page.root.querySelectorAll('.sm-hovers .sm-rname').map(t => t.textContent).join(' ');
    if (set) { named++; assert.equal(set, title, 'its own name, whole'); }
    glyph.fire('pointerleave', { pointerType: 'mouse' });
    assert.equal(page.root.querySelectorAll('.sm-hovers .sm-rname').length, 0);
  });
  assert.ok(named >= 0.75 * glyphs.length, named + ' of ' + glyphs.length + ' named beside their glyphs');
  const id = isolated(scene) || busiest(scene);
  page.map.select(id);
  const chosen = page.root.querySelector('.sm-node--comp[data-sm-key="comp:' + id + '"]');
  chosen.fire('pointerenter', { pointerType: 'mouse' });
  assert.match(page.textOf(out), /Click again to open its page/);
});

/* ---- Names ------------------------------------------------------------------------ */
test('on the landing a choice names its linked components on plates, no two of them overlapping', async () => {
  const scene = liveScene();
  const page = await mount({ scene, areaWidth: 820 });
  page.map.select(busiest(scene));
  const plates = page.root.querySelectorAll('.sm-plate');
  assert.ok(plates.length > 0);
  assert.equal(page.map.snapshot().lit.plates, plates.length);
  const boxes = plates.map(g => { const r = g.querySelector('rect'); return [+r.getAttribute('x'), +r.getAttribute('y'), +r.getAttribute('width'), +r.getAttribute('height')]; });
  boxes.forEach((a, i) => boxes.forEach((b, j) => {
    if (j <= i) return;
    const apart = a[0] + a[2] <= b[0] || b[0] + b[2] <= a[0] || a[1] + a[3] <= b[1] || b[1] + b[3] <= a[1];
    assert.ok(apart, 'two plates overlap');
  }));
  plates.forEach(g => assert.ok(page.root.querySelector('.sm-node--comp[data-sm-key="' + g.getAttribute('data-sm-plate') + '"]').classList.contains('is-lit') ||
    page.root.querySelector('.sm-node--comp[data-sm-key="' + g.getAttribute('data-sm-plate') + '"]').classList.contains('is-self')));
  const vb = page.root.querySelector('svg.sm-ring').getAttribute('viewBox').split(' ').map(Number);
  plates.forEach(g => pointsOf(g.querySelector('.sm-leader').getAttribute('d')).forEach(([x, y]) =>
    assert.ok(x >= 0 && x <= vb[2] && y >= 0 && y <= vb[3], 'a leader stays on the drawing')));
});

test('names come by levels of detail: none round the rim at rest, a family’s own on its closer look, a plate never twice', async () => {
  // Will (5 October 2026, through the design review): the permanent fringe
  // of every name round the rim gives way to levels of detail.
  const scene = liveScene();
  const page = await mount({ scene, explorer: true, areaWidth: 1900, areaHeight: 950 });
  assert.equal(page.root.querySelectorAll('.sm-rimname').length, 0, 'at rest, the families are the landmarks');
  const labelOf = n => { const d = scene.scene.inspectors[n.inspector_ref || 'inspector:' + n.id] || {}; return d.public_label || d.title || n.label; };
  const fam = 'formal_math_and_proof';
  page.map.select('area:' + fam);
  const cam = page.map.snapshot().camera;
  const members = compNodes(scene).filter(n => n.parent_cluster_id === 'cluster:' + fam);
  if (cam) {
    assert.equal(cam.names, 'area:' + fam);
    assert.deepEqual(page.root.querySelectorAll('.sm-rimname--cam').map(n => n.textContent).sort(), members.map(labelOf).sort(),
      'its closer look names its own components and no other');
  }
  // A zoom names what stands whole; a component it names gets no plate.
  page.map.select(busiest(scene));
  page.section.fire('explorer:zoom', { detail: { direction: 1 } });
  assert.equal(page.map.snapshot().camera.names, 'all');
  page.root.querySelectorAll('.sm-plate').forEach(p => {
    const key = p.getAttribute('data-sm-plate');
    assert.equal(page.root.querySelector('.sm-node--comp[data-sm-key="' + key + '"] .sm-rimname'), null, 'a plate for ' + key + ' and its name both');
  });
});

/* ---- The explorer (docs/system-map.html, 5 October 2026) ---------------------- */
const codeOf = scene => scene.scene.edges.filter(e => CODE_RELATIONS.includes(e.relation));
function mostConnected(scene) {
  const tally = {};
  codeOf(scene).forEach(e => { tally[e.source] = (tally[e.source] || 0) + 1; tally[e.target] = (tally[e.target] || 0) + 1; });
  return Object.entries(tally).sort((x, y) => y[1] - x[1] || (x[0] < y[0] ? -1 : 1))[0][0];
}
test('the explorer fits the whole circle to its stage, names only the families at rest, and keeps its words in the panel', async () => {
  const scene = typedScene();
  for (const [w, hh] of [[922, 630], [1037, 730], [1400, 893], [2040, 1253]]) {
    const page = await mount({ scene, explorer: true, areaWidth: w, areaHeight: hh });
    const s = page.map.snapshot(), f = s.ring.frame;
    // The ring, its scale and the family names round it (about 75px past
    // the marks) stand inside the stage with a margin; the circle fills it.
    const reach = +f.R + 70, half = Math.min(w, hh) / 2;
    assert.ok(+f.cx - reach >= 0 && +f.cx + reach <= w && +f.cy - reach >= 0 && +f.cy + reach <= hh, `the whole circle stands in ${w}x${hh}`);
    assert.ok(+f.R > half - 140, `and fills it at ${w}x${hh}`);
    const nx = Math.min(Math.max(+f.cx, w - 254), w - 14), ny = Math.min(Math.max(+f.cy, 14), 50);
    assert.ok(Math.hypot(nx - f.cx, ny - f.cy) >= +f.R + 60, 'clear of the controls in the top right');
    assert.equal(s.camera, null);
    assert.equal(page.root.querySelectorAll('.sm-rimname').length, 0, 'no component named round the rim at rest');
    assert.equal(page.root.querySelectorAll('.sm-node--fam').length, s.counts.families, 'every family named round the outside');
    assert.equal(page.root.querySelector('.sm-caption'), null, 'the stage carries no sentence');
    assert.equal(page.root.querySelector('.sm-back'), null, 'and no way back of its own');
    const trail = page.headEl.querySelector('.sm-trail');
    assert.ok(trail && trail.hidden, 'the trail waits in the panel head');
    assert.equal(page.keySlot.querySelector('.sm-key__more'), null, 'the stage key is one row');
    assert.ok(page.about.querySelector('.sm-key--panel .sm-key__about'), 'every mark is named in the panel');
    assert.ok(page.host.querySelector('.sc-doctrine__go'), 'the way into the doctrine stands under the families');
  }
  // A phone's stage is too small for the names round the outside: the ring
  // takes their room, and the families are named all together or not at all.
  const phone = await mount({ scene, explorer: true, areaWidth: 390, areaHeight: 600 });
  const ps = phone.map.snapshot();
  assert.equal(ps.ring.crowded, true);
  assert.ok([0, ps.counts.families].includes(phone.root.querySelectorAll('.sm-node--fam').length), 'never a lone family name');
  assert.ok(+ps.ring.frame.R > 390 / 2 - 80, 'the ring takes the room the names would have taken');
});

/* ---- The explorer's inspector (6 October 2026) --------------------------------- */
// A Type B review of the system view: a component's rules sat below its
// forty-two connections, each row repeated its family, the doctrine was one
// list, and the drawing highlighted without letting one relation be read.
const VERBS = { runs: ['Runs', 'Run by'], reads_results_of: ['Reads the saved results of', 'Its saved results are read by'],
                checks_copies_of: ['Checks the copied files of', 'Its copied files are checked by'] };
const tabsOf = pg => pg.querySelectorAll('.sc__tab');
const tabFor = (pg, view) => tabsOf(pg).find(t => t.getAttribute('data-view') === view);
const panelOf = (pg, tab) => pg.querySelector('[id="' + tab.getAttribute('aria-controls') + '"]');
const showView = (page, view) => { const t = tabFor(page.panel(), view); page.click(t); return panelOf(page.panel(), t); };
const famTitles = scene => Object.fromEntries(scene.scene.nodes.filter(n => n.kind === 'area').map(n => [n.id.replace('area:', ''), n.label]));
const titleOfComp = (scene, id) => (scene.scene.inspectors['inspector:' + id] || {}).public_label || scene.scene.nodes.find(n => n.id === id).label;

test('a choice in the explorer: a compact head, its ways out by weight, then one strip of views over its relations', async () => {
  const scene = typedScene(), doctrine = doctrineFor(scene);
  const page = await mount({ scene, doctrine, explorer: true, areaWidth: 1037, areaHeight: 730 });
  const id = mostConnected(scene);
  page.map.select(id);
  assert.equal(page.map.snapshot().view, 'component');
  assert.ok(page.headEl.classList.contains('is-collapsed'), 'the introduction gives way to the trail');
  const trail = page.headEl.querySelector('.sm-trail');
  assert.equal(trail.hidden, false);
  const fam = famOf(scene)[id];
  assert.deepEqual(trail.querySelectorAll('.sm-crumbs__go').map(b => b.textContent), ['The system map', famTitles(scene)[fam]]);
  const pg = page.panel();
  assert.ok(pg.children[0].classList.contains('sc__head'));
  assert.equal(pg.querySelector('.sc__title').tagName, 'H2');
  assert.equal(pg.querySelector('.sc__kicker'), null, 'its family is said once, in the trail');
  assert.equal(pg.querySelector('.sc__all'), null, 'nothing waits behind "show all"');
  // Its ways out by weight: its page, its paper module, its source quietly.
  const ways = pg.children[1];
  assert.ok(ways.classList.contains('sc__actions'));
  const links = ways.querySelectorAll('a');
  assert.deepEqual(links.map(a => a.textContent.replace(/ on GitHub$/, '')), ['Component page', 'Paper module', 'Source']);
  assert.deepEqual(links.map(a => a.getAttribute('class').split(' ')[1]), ['sc__go--primary', 'sc__go--secondary', 'sc__go--quiet']);
  // One strip of views: the overview, the connections, the rules, each with
  // the count of what it holds.
  const edges = codeOf(scene).filter(e => e.source === id || e.target === id);
  const row = doctrine.components.find(c => c.id === id);
  const cited = row.governed_by.length + row.abides_by.length;
  assert.equal(pg.querySelector('.sc__tablist').getAttribute('role'), 'tablist');
  const tabs = tabsOf(pg);
  assert.deepEqual(tabs.map(t => t.textContent), ['Overview', 'Connections' + edges.length, 'Rules' + cited]);
  tabs.forEach(t => {
    assert.equal(t.getAttribute('role'), 'tab');
    const p = panelOf(pg, t);
    assert.equal(p.getAttribute('role'), 'tabpanel');
    assert.equal(p.getAttribute('aria-labelledby'), t.getAttribute('id'));
  });
  assert.deepEqual(tabs.map(t => t.getAttribute('aria-selected')), ['true', 'false', 'false']);
  assert.deepEqual(tabs.map(t => panelOf(pg, t).hidden), [false, true, true]);
  assert.deepEqual(tabs.map(t => t.getAttribute('tabindex')), ['0', '-1', '-1'], 'one tab stop for the strip');
  // The arrows, Home and End move along the strip and show each view at once.
  tabs[0].fire('keydown', { key: 'ArrowRight' });
  assert.deepEqual(tabs.map(t => t.getAttribute('aria-selected')), ['false', 'true', 'false']);
  assert.equal(panelOf(pg, tabs[1]).hidden, false);
  tabs[1].fire('keydown', { key: 'End' });
  assert.equal(tabs[2].getAttribute('aria-selected'), 'true');
  tabs[2].fire('keydown', { key: 'ArrowRight' });
  assert.equal(tabs[0].getAttribute('aria-selected'), 'true', 'and round from the last to the first');
  // The overview: its relations in a line or two each, each a way to its view,
  // then its whole description.
  const ov = panelOf(pg, tabs[0]);
  const sums = ov.querySelectorAll('.sc__sum-go');
  assert.deepEqual(sums.map(b => b.getAttribute('data-to-view')), ['code', 'rules']);
  assert.match(page.textOf(sums[0]), new RegExp('^' + edges.length + ' code connections'));
  assert.match(page.textOf(sums[1]), new RegExp('^' + cited + ' rules its paper module cites'));
  page.click(sums[1]);
  assert.equal(tabs[2].getAttribute('aria-selected'), 'true');
  const d = scene.scene.inspectors['inspector:' + id] || {};
  const whole = page.core.trimProse(d.what_it_does, 1e6);
  if (whole && whole !== d.summary_line) {
    const about = ov.querySelector('.sc__section--about');
    assert.equal(page.textOf(about.querySelector('.sc__section-title')), 'What it does');
    assert.equal(about.querySelector('.sc__body').textContent, whole, 'the whole description, every plain sentence');
  }
  // Connections: under the verb that names each from this component's side,
  // out before in, then by family round the ring, the family named once.
  const code = panelOf(pg, tabs[1]);
  const want = [];
  Object.entries(VERBS).forEach(([rel, [out, inc]]) => {
    if (edges.some(e => e.relation === rel && e.source === id)) want.push(out);
    if (edges.some(e => e.relation === rel && e.target === id)) want.push(inc);
  });
  assert.deepEqual(code.querySelectorAll('.sc__rel-title').map(l => l.children[0].textContent), want);
  assert.equal(code.querySelectorAll('.sc__li').length, edges.length, 'one row for each connection');
  assert.equal(code.querySelectorAll('.sc__item-note').length, 0, 'no family repeated after a name');
  assert.equal(code.querySelectorAll('.sc__item--rule').length, 0, 'no rule among the code connections');
  const titles = famTitles(scene), labelOf = Object.fromEntries(Object.entries(titles).map(([k, v]) => [v, k]));
  code.querySelectorAll('.sc__rel').forEach(sec => {
    const heading = sec.querySelector('.sc__rel-title').children[0].textContent;
    const [rel, dir] = Object.entries(VERBS).flatMap(([r, [o, i]]) => [[r, 'out', o], [r, 'inc', i]]).find(v => v[2] === heading);
    sec.querySelectorAll('.sc__famgroup').forEach(g => {
      const famKey = labelOf[g.querySelector('.sc__fam-name').textContent];
      const ks = g.querySelectorAll('.sc__li').map(li => +li.getAttribute('data-k'));
      assert.deepEqual(ks, ks.slice().sort((a, b) => a - b), 'the scene’s order within a family');
      g.querySelectorAll('.sc__li').forEach(li => {
        const other = keyOf(li.querySelector('.sc__item')).slice(5);
        assert.equal(famOf(scene)[other], famKey, 'each row under its own family');
        assert.ok(edges.some(e => e.relation === rel && (dir === 'out' ? e.source === id && e.target === other : e.target === id && e.source === other)),
          'each row is the relation its heading names, the right way round: ' + heading + ' ' + other);
      });
    });
  });
  // The rules: their own view, under their own heading, a rule shown holding
  // here marked in words.
  const rules = panelOf(pg, tabs[2]);
  assert.match(page.textOf(rules.querySelector('.sc__section-title')), new RegExp('^Rules its paper module cites · ' + cited + '$'));
  assert.equal(rules.querySelectorAll('.sc__list--rules .sc__item--rule').length, cited);
  assert.equal(rules.querySelectorAll('.sc__item').filter(b => !b.classList.contains('sc__item--rule')).length, 0, 'no component among the rules');
  rules.querySelectorAll('.sc__held').forEach(t => assert.match(page.textOf(t), /^(Enforced here|Partly checked here)$/));
  // In the manifest's order: its principles, then its axioms.
  const order = [...doctrine.principles, ...doctrine.axioms].map(r => r.id);
  const ids = rules.querySelectorAll('.sc__list--rules .sc__item--rule').map(ruleKey);
  assert.deepEqual(ids, ids.slice().sort((a, b) => order.indexOf(a) - order.indexOf(b)));
});

test('the rules stay one step away at any number of connections, and a component with none keeps the view and says so', async () => {
  const scene = typedScene(), doctrine = doctrineFor(scene);
  const page = await mount({ scene, doctrine, explorer: true, areaWidth: 1037, areaHeight: 730 });
  const tally = {};
  codeOf(scene).forEach(e => { tally[e.source] = (tally[e.source] || 0) + 1; tally[e.target] = (tally[e.target] || 0) + 1; });
  const busy = mostConnected(scene), none = compNodes(scene).map(n => n.id).find(x => !tally[x]);
  assert.ok(busy && none);
  page.map.select(busy);
  const rp = showView(page, 'rules');
  const cites = id => { const r = doctrine.components.find(c => c.id === id); return r.governed_by.length + r.abides_by.length; };
  assert.equal(rp.querySelectorAll('.sc__list--rules .sc__item--rule').length, cites(busy));
  // The view holds from one choice to the next.
  page.map.select(none);
  assert.equal(tabsOf(page.panel()).find(t => t.getAttribute('aria-selected') === 'true').getAttribute('data-view'), 'rules');
  assert.equal(panelOf(page.panel(), tabFor(page.panel(), 'rules')).querySelectorAll('.sc__list--rules .sc__item--rule').length, cites(none));
  // No connection: the view stays, says so in a sentence, and leads to the rules.
  assert.equal(tabFor(page.panel(), 'code').textContent, 'Connections0');
  const cp = showView(page, 'code');
  assert.equal(cp.querySelector('.sc__zero').textContent, 'No code connections of the kinds the map draws.');
  assert.match(page.textOf(cp), /Its code does not run another component, read another’s saved results or check another’s copied files, and no other component’s code does any of these to it\./);
  const jump = cp.querySelector('.sc__jump');
  assert.equal(jump.textContent, cites(none) + ' ' + (cites(none) === 1 ? 'rule' : 'rules') + ' its paper module cites');
  page.press(jump);
  assert.equal(tabFor(page.panel(), 'rules').getAttribute('aria-selected'), 'true');
  // The drawing follows the view: its connections view steps the rule lines
  // back and names no rule; its rules view names no component but itself.
  page.map.select(busy);
  const svg = () => page.root.querySelector('.sm-ring');
  showView(page, 'code');
  assert.ok(svg().classList.contains('is-view-code'));
  assert.equal(page.root.querySelectorAll('.sm-tags .sm-rname-g').length, 0);
  showView(page, 'rules');
  assert.ok(svg().classList.contains('is-view-rules'));
  page.root.querySelectorAll('.sm-plate').forEach(p => assert.equal(p.getAttribute('data-sm-plate'), 'comp:' + busy));
  showView(page, 'overview');
  assert.ok(!svg().classList.contains('is-view-code') && !svg().classList.contains('is-view-rules'));
});

test('pointing at a connection’s row draws that one relation whole, and moves neither the camera nor the choice', async () => {
  const scene = codeScene(), fan = widestFan(scene);
  const page = await mount({ scene, doctrine: doctrineFor(scene), explorer: true, areaWidth: 1400, areaHeight: 893, reduce: true });
  page.map.select(fan.hub);
  const cp = showView(page, 'code');
  const before = plain(page.map.snapshot());
  const reads = cp.querySelectorAll('.sc__rel').find(sec => sec.querySelector('.sc__rel-title').children[0].textContent === 'Reads the saved results of');
  // A connection out to another family, whose route crosses the ring.
  const rows = reads.querySelectorAll('.sc__li').filter(r => famOf(scene)[keyOf(r.querySelector('.sc__item')).slice(5)] !== famOf(scene)[fan.hub]);
  const li = rows[Math.min(3, rows.length - 1)], btn = li.querySelector('.sc__item');
  btn.fire('pointerenter');
  const after = plain(page.map.snapshot());
  assert.deepEqual(after.camera, before.camera, 'the camera stays');
  assert.equal(after.component, fan.hub, 'the choice stays');
  assert.ok(page.root.querySelector('.sm-ring').classList.contains('is-tracing'));
  const traced = page.root.querySelectorAll('.sm-trace .sm-route');
  assert.equal(traced.length, 1, 'one relation, drawn whole along its own route');
  assert.equal(traced[0].getAttribute('data-k'), li.getAttribute('data-k'));
  const other = keyOf(btn);
  assert.deepEqual([traced[0].getAttribute('data-from'), traced[0].getAttribute('data-to')].sort(), ['comp:' + fan.hub, other].sort());
  assert.ok(page.root.querySelector('.sm-trace .sm-trace__dir'), 'with a chevron the way the code acts');
  // Its readout says the relation as a sentence, the component that acts first.
  const name = id => titleOfComp(scene, id);
  assert.ok(page.root.querySelector('.sm-readout').textContent.includes(name(fan.hub) + ' reads the saved results of ' + name(other.slice(5)) + '.'));
  btn.fire('pointerleave');
  assert.equal(page.root.querySelectorAll('.sm-trace .sm-route').length, 0);
  assert.ok(!page.root.querySelector('.sm-ring').classList.contains('is-tracing'));
  // Each row's way to the code is the file of its own connection, named for what it opens.
  page.panel().querySelectorAll('.sc__list--code .sc__code').forEach(a => {
    assert.equal(a.textContent, 'Source file');
    assert.match(a.getAttribute('aria-label'), /^Source file establishing this connection, on GitHub: /);
    assert.match(a.getAttribute('href'), /^https:\/\/github\.com\/[^/]+\/[^/]+\/blob\/[^/]+\/[^#]+$/);
  });
});

test('a family of connections chosen in the panel stands alone on the drawing, labelled with what it shows of the whole; a find narrows both', async () => {
  const scene = codeScene(), fan = widestFan(scene), edges = codeOf(scene).filter(e => e.source === fan.hub || e.target === fan.hub);
  const page = await mount({ scene, doctrine: doctrineFor(scene), explorer: true, areaWidth: 1400, areaHeight: 893, reduce: true });
  page.map.select(fan.hub);
  const camera = plain(page.map.snapshot().camera);
  let cp = showView(page, 'code');
  const groups = cp.querySelectorAll('.sc__famgroup');
  const g = groups.slice().sort((a, b) => b.querySelectorAll('.sc__li').length - a.querySelectorAll('.sc__li').length)[0];
  const fb = g.querySelector('.sc__fam'), n = +fb.querySelector('.sc__fam-n').textContent;
  const keep = g.querySelectorAll('.sc__li').map(li => li.getAttribute('data-k'));
  assert.equal(n, keep.length);
  page.click(fb);
  assert.equal(fb.getAttribute('aria-pressed'), 'true');
  const svg = page.root.querySelector('.sm-ring');
  assert.ok(svg.classList.contains('is-narrowed'));
  const scoped = page.root.querySelectorAll('.sm-scoped .sm-route');
  assert.deepEqual(scoped.map(p => p.getAttribute('data-k')).sort(), keep.slice().sort(), 'its connections, each its own route');
  assert.deepEqual(plain(page.map.snapshot().camera), camera, 'the camera stays');
  const bar = page.host.querySelector('.sc__scopebar');
  assert.ok(bar, 'the narrowing is labelled');
  assert.match(page.textOf(bar), new RegExp('^The map shows ' + n + ' of ' + edges.length + ' code connections: reads the saved results of '));
  assert.equal(cp.querySelectorAll('.sc__li').filter(li => !li.hidden).length, edges.length, 'the panel keeps every row');
  // Plates name only what it shows.
  const kept = new Set(g.querySelectorAll('.sc__item').map(keyOf).concat(['comp:' + fan.hub]));
  page.root.querySelectorAll('.sm-plates .sm-plate').forEach(p => assert.ok(kept.has(p.getAttribute('data-sm-plate')), p.getAttribute('data-sm-plate')));
  // A ribbon's count is of the connections it carries, one kind to one family.
  page.root.querySelectorAll('.sm-count-g').forEach(c => {
    const fam = c.getAttribute('data-sm-count'), kind = c.getAttribute('data-kind');
    assert.equal(kind, 'reads');
    assert.ok(+c.getAttribute('data-n') <= edges.filter(e => famOf(scene)[e.target] === fam && e.source === fan.hub).length);
  });
  // Show all lets it go.
  page.press(bar.querySelector('.sc__scopebar-all'));
  assert.ok(!svg.classList.contains('is-narrowed'));
  assert.equal(page.root.querySelectorAll('.sm-scoped .sm-route').length, 0);
  assert.equal(page.host.querySelector('.sc__scopebar'), null);
  assert.ok(page.panel().querySelectorAll('.sc__fam').every(b => b.getAttribute('aria-pressed') === 'false'));
  // A find narrows the list and the drawing together, and says how many it shows.
  cp = panelOf(page.panel(), tabFor(page.panel(), 'code'));
  const input = cp.querySelector('.sc__find-input');
  assert.ok(input, 'a long list has a find');
  const famKey = famOf(scene)[keyOf(g.querySelector('.sc__item')).slice(5)], title = famTitles(scene)[famKey];
  input.value = title.toLowerCase();
  input.fire('input');
  const shown = cp.querySelectorAll('.sc__li').filter(li => !li.hidden);
  const wantN = edges.filter(e => famOf(scene)[e.source === fan.hub ? e.target : e.source] === famKey).length;
  assert.equal(shown.length, wantN);
  assert.match(cp.querySelector('.sc__find-n').textContent, new RegExp('^Showing ' + wantN + ' of ' + edges.length + ' code connections\\.$'));
  assert.equal(page.root.querySelectorAll('.sm-scoped .sm-route').length, wantN);
  // Kept through a rebuild (full screen redraws the map; the doctrine arriving rebuilds the panel).
  page.map.snapshot();
  assert.equal(page.host.querySelector('.sc__find-input').value, title.toLowerCase());
});

test('the doctrine opens on its three kinds, each in the manifest’s order, with one find over all of them', async () => {
  const scene = typedScene(), doctrine = doctrineFor(scene);
  const page = await mount({ scene, doctrine, explorer: true, areaWidth: 1400, areaHeight: 893, reduce: true });
  page.map.select('doctrine');
  const pg = page.panel();
  const tabs = tabsOf(pg);
  assert.deepEqual(tabs.map(t => t.textContent), ['Axioms12', 'Principles20', 'Failure modes17']);
  const names = tab => panelOf(pg, tab).querySelectorAll('.sc__li').filter(li => !li.hidden).map(li => li.querySelector('.sc__item-name').textContent);
  assert.deepEqual(names(tabs[0]), AXIOMS);
  assert.doesNotMatch(page.textOf(pg.querySelector('.sc__head')), /sits just outside/, 'the note on where rules sit waits at the end');
  const named = () => page.root.querySelectorAll('.sm-tags .sm-rname-g').map(g => g.getAttribute('data-sm-name').slice(5));
  assert.ok(named().length >= 8 && named().every(r => /^AX-/.test(r)));
  page.click(tabs[1]);
  assert.deepEqual(names(tabs[1]), PRINCIPLES);
  assert.ok(named().length > 0 && named().every(r => /^P-/.test(r)), 'the drawing names the kind open in the panel');
  assert.ok(page.root.querySelector('.sm-ring').classList.contains('is-cat-principle'));
  tabs[1].fire('keydown', { key: 'ArrowRight' });
  assert.deepEqual(names(tabs[2]), FAILURES);
  assert.ok(named().every(r => /^AP-/.test(r)));
  // One find over all three, its counts on the tabs.
  const input = pg.querySelector('.sc__find-input');
  assert.equal(input.getAttribute('placeholder'), 'Find a rule or failure mode');
  page.click(tabs[1]);
  input.value = 'provenance';
  input.fire('input');
  assert.deepEqual(names(tabs[1]), PRINCIPLES.filter(t => /provenance/i.test(t)));
  assert.deepEqual(tabs.map(t => t.textContent), ['Axioms1 of 12', 'Principles2 of 20', 'Failure modes0 of 17']);
  assert.equal(pg.querySelector('.sc__find-n').textContent, 'Two of the 20 principles match. Also 1 axiom under its own view.');
  input.fire('keydown', { key: 'Escape' });
  assert.equal(input.value, '');
  assert.deepEqual(tabs.map(t => t.textContent), ['Axioms12', 'Principles20', 'Failure modes17']);
  // How the diagram is arranged, at the end.
  const how = pg.querySelector('.sc__how');
  assert.equal(how.querySelector('.sc__how-summary').textContent, 'How this diagram is arranged');
  const flow = pg.querySelector('.sc__flow');
  assert.equal(flow.children[flow.children.length - 1], how);
  assert.match(page.textOf(how), /A rule tied to one axiom sits just outside it; a rule tied to several stands on the ring between them\./);
  assert.doesNotMatch(visibleText(page.host), UNPLAIN);
});

test('a rule’s evidence: enforced, partly checked and cited are three lists that never stand for one another', async () => {
  const scene = liveScene(), doctrine = doctrineFor(scene);
  [...doctrine.axioms, ...doctrine.principles, ...doctrine.anti_principles].forEach(r => {
    r.named_in_card = r.enforced_in.slice(); r.enforced_in = []; r.partly_enforced_in = [];
  });
  const citers = doctrine.components.filter(c => c.governed_by.includes('P-3')).map(c => c.id);
  assert.ok(citers.length >= 3);
  const [full, part, other] = citers;
  const p = doctrine.principles[2];
  p.enforced_in = [full]; p.partly_enforced_in = [part]; p.named_in_card = [full, part];
  const page = await mount({ scene, doctrine, explorer: true, areaWidth: 1400, areaHeight: 893, reduce: true });
  page.map.select('doctrine:P-3');
  const pg = page.panel();
  const sections = pg.querySelectorAll('.sc__section').map(s => page.textOf(s.querySelector('.sc__section-title')));
  assert.deepEqual(sections, ['Foundations and threats', 'Evidence in components', 'Citation reach'], 'meaning, ties, evidence, reach, in that order');
  const ties = pg.querySelector('.sc__section--ties');
  assert.match(page.textOf(ties), /Rests on · \d/);
  const ev = pg.querySelector('.sc__section--evidence');
  const block = label => ev.querySelectorAll('.sc__block').find(b => page.textOf(b.querySelector('.sc__label')).startsWith(label));
  assert.deepEqual(block('Enforced in').querySelectorAll('.sc__item').map(keyOf), ['comp:' + full]);
  assert.deepEqual(block('Partly checked in').querySelectorAll('.sc__item').map(keyOf), ['comp:' + part]);
  ev.querySelectorAll('.sc__code').forEach(a => { assert.equal(a.textContent, 'Evidence record'); assert.match(a.getAttribute('href'), /#evidence$/); });
  const reach = pg.querySelector('.sc__section--reach');
  assert.match(page.textOf(reach), new RegExp('Cited by the paper modules of ' + citers.length + ' of ' + compNodes(scene).length + ' components'));
  assert.doesNotMatch(page.textOf(pg), /cited only|cited-only|without a test: \d/i, 'no count read off the others');
  // A rule enforced in one component is marked there alone.
  const held = id => {
    page.map.select(id);
    const rp = showView(page, 'rules');
    const row = rp.querySelectorAll('.sc__list--rules .sc__item--rule').find(b => ruleKey(b) === 'P-3');
    const t = row && row.querySelector('.sc__held');
    return t ? t.textContent : null;
  };
  assert.equal(held(full), 'Enforced here');
  assert.equal(held(part), 'Partly checked here');
  assert.equal(held(other), null, 'citing it is no mark of a check');
  // And the drawing says the same when the rule is pointed at in a component's view.
  page.map.select(other);
  const rp = showView(page, 'rules');
  rp.querySelectorAll('.sc__item--rule').find(b => ruleKey(b) === 'P-3').fire('pointerenter');
  assert.match(page.root.querySelector('.sm-readout').textContent, /Its paper module cites this rule\. No test marks it here\./);
  page.map.select(full);
  showView(page, 'rules').querySelectorAll('.sc__item--rule').find(b => ruleKey(b) === 'P-3').fire('pointerenter');
  assert.match(page.root.querySelector('.sm-readout').textContent, /Its paper module cites this rule\. Enforced here: a test shows the rule’s core requirement in this component\./);
});

test('the explorer’s panel folds away from a control of its own in the stage', async () => {
  const page = await mount({ explorer: true, areaWidth: 1037, areaHeight: 730 });
  const tools = page.stage.querySelector('.explorer__tools');
  const fold = tools.querySelector('[data-explorer-panel-toggle]');
  assert.ok(fold, 'a way to fold the panel stands with the map’s controls');
  assert.equal(fold.getAttribute('aria-expanded'), 'true');
  assert.equal(fold.querySelector('[data-explorer-panel-label]').textContent, 'Hide panel');
  assert.equal(tools.children[0], fold, 'first among them, nearest the panel');
});

/* ---- Readable selection (6 October 2026) ------------------------------------- */
// A Type B review found the drawing naming a component a rule touches but not
// the rule itself; Will then asked for the map to be "lightning fast".
const allRules = doctrine => [...doctrine.axioms, ...doctrine.principles, ...doctrine.anti_principles];
const boxOfRect = rect => {
  const x0 = +rect.getAttribute('x'), y0 = +rect.getAttribute('y');
  return { x0, y0, x1: x0 + +rect.getAttribute('width'), y1: y0 + +rect.getAttribute('height') };
};
const placeOf = node => {
  const m = /translate\((-?[\d.]+) (-?[\d.]+)\)/.exec(node.getAttribute('transform'));
  return [+m[1], +m[2]];
};
test('the chosen rule wears a tag beside its glyph: its whole name, clear of every glyph and mark', async () => {
  const scene = typedScene(), doctrine = doctrineFor(scene);
  const page = await mount({ scene, doctrine, explorer: true, areaWidth: 2040, areaHeight: 1253, reduce: true });
  let tagged = 0;
  for (const r of allRules(doctrine).slice(0, 12)) {
    page.map.select('doctrine:' + r.id);
    const tags = page.root.querySelectorAll('.sm-tag');
    assert.ok(tags.length <= 1, 'one tag at a time');
    if (!tags.length) continue;
    tagged++;
    const tag = tags[0];
    assert.equal(tag.getAttribute('data-sm-tag'), 'rule:' + r.id);
    assert.equal(tag.querySelectorAll('.sm-tag__title').map(t => t.textContent).join(' '), r.title, 'its whole name');
    const b = boxOfRect(tag.querySelector('.sm-tag__box'));
    page.root.querySelectorAll('.sm-node--rule, .sm-node--comp').forEach(n => {
      const [x, y] = placeOf(n);
      assert.ok(x < b.x0 - 4 || x > b.x1 + 4 || y < b.y0 - 4 || y > b.y1 + 4, 'the tag stands clear of ' + n.getAttribute('data-sm-key'));
    });
  }
  assert.ok(tagged >= 10, tagged + ' of 12 rules tagged in a large explorer');
});

test('a component’s view names the rules it cites and those shown holding there, each beside its glyph', async () => {
  const scene = typedScene(), doctrine = doctrineFor(scene);
  const page = await mount({ scene, doctrine, explorer: true, areaWidth: 2040, areaHeight: 1253, reduce: true });
  const id = mostConnected(scene);
  page.map.select(id);
  const row = doctrine.components.find(c => c.id === id);
  const held = allRules(doctrine).filter(r => (r.enforced_in || []).includes(id)).map(r => r.id);
  const allowed = new Set([...row.governed_by, ...row.abides_by, ...held]);
  const titles = Object.fromEntries(allRules(doctrine).map(r => [r.id, r.title]));
  const names = page.root.querySelectorAll('.sm-tags .sm-rname-g');
  assert.ok(names.length > 0 && names.length <= 8, names.length + ' names');
  names.forEach(g => {
    const rid = g.getAttribute('data-sm-name').slice(5);
    assert.ok(allowed.has(rid), 'only a rule the view lights is named: ' + rid);
    assert.equal(g.querySelectorAll('.sm-rname').map(t => t.textContent).join(' '), titles[rid], 'its whole name');
  });
  // The doctrine's own view names its axioms.
  page.map.select('doctrine');
  const axioms = page.root.querySelectorAll('.sm-tags .sm-rname-g').map(g => g.getAttribute('data-sm-name').slice(5));
  assert.ok(axioms.length >= 8 && axioms.every(a => /^AX-/.test(a)), axioms.join(' '));
});

test('a choice that needs a new view sets off at once, and the new view is drawn once that frame is shown', async () => {
  const scene = typedScene();
  // A component its choice brings the camera closer to.
  const probe = await mount({ scene, explorer: true, areaWidth: 1037, areaHeight: 730, reduce: true });
  const id = compNodes(scene).map(n => n.id).find(c => { probe.map.select(c, { instant: true }); return !!probe.map.snapshot().camera; });
  assert.ok(id, 'some choice moves the camera');
  const page = await mount({ scene, explorer: true, areaWidth: 1037, areaHeight: 730, visible: true });
  const old = page.root.querySelector('.sm-body'), n0 = page.animations.length;
  page.map.select(id);
  const moved = page.animations.slice(n0).filter(a => a.el === old && a.frames.some(f => f.transform));
  assert.equal(moved.length, 1, 'the view on screen sets off in the click’s own frame');
  assert.equal(page.root.querySelectorAll('.sm-body').length, 1, 'the new view is not drawn yet');
  assert.ok(page.map.snapshot().camera, 'and the camera is already the new one');
  page.flushFrames();
  const bodies = page.root.querySelectorAll('.sm-body');
  assert.equal(bodies.length, 1, 'once the frame is shown the new view is drawn and the old one let go');
  assert.notEqual(bodies[0], old);
  assert.equal(page.map.snapshot().view, 'component');
  // A page that is not painting (hidden, or with no frames) draws at once.
  const quiet = await mount({ scene, explorer: true, areaWidth: 1037, areaHeight: 730 });
  const old2 = quiet.root.querySelector('.sm-body');
  quiet.map.select(id);
  assert.ok(quiet.root.querySelectorAll('.sm-body').some(b => b !== old2), 'drawn in the same call');
});

test('the explorer zooms and fits when its frame asks; a closer look names the components that stand whole; a new choice frames itself', async () => {
  const scene = typedScene();
  const page = await mount({ scene, explorer: true, areaWidth: 1037, areaHeight: 730, reduce: true });
  page.map.select('area:formal_math_and_proof');
  page.section.fire('explorer:fit', { detail: {} });
  assert.equal(page.map.snapshot().camera, null, 'Fit shows the whole map');
  assert.equal(page.map.snapshot().view, 'family', 'and keeps the choice');
  page.section.fire('explorer:zoom', { detail: { direction: 1 } });
  const one = page.map.snapshot().camera;
  assert.ok(one && one.k > 1.5 && one.names === 'all');
  page.section.fire('explorer:zoom', { detail: { direction: 1 } });
  const two = page.map.snapshot().camera;
  assert.ok(two.k > one.k * 1.5);
  const names = page.root.querySelectorAll('.sm-rimname--cam');
  assert.ok(names.length > 0, 'close enough, components are named');
  // Each name stands whole inside the drawing.
  const vb = page.root.querySelector('svg.sm-ring').getAttribute('viewBox').split(' ').map(Number);
  assert.ok(vb[2] === 1037 && vb[3] === 730);
  page.section.fire('explorer:zoom', { detail: { direction: -1 } });
  page.section.fire('explorer:zoom', { detail: { direction: -1 } });
  page.section.fire('explorer:zoom', { detail: { direction: -1 } });
  assert.equal(page.map.snapshot().camera, null, 'zooming out comes back to the whole map, never past it');
  page.section.fire('explorer:zoom', { detail: { direction: 1 } });
  page.map.select(mostConnected(scene));
  const cam = page.map.snapshot().camera;
  assert.ok(!cam || cam.names !== 'all', 'a new choice lets the zoom go and frames itself');
});

test('click-and-hold pans the fitted map and Fit restores it without selecting a node', async () => {
  const page = await mount({ scene: typedScene(), explorer: true, areaWidth: 1037, areaHeight: 730, reduce: true });
  const area = page.root.querySelector('.sm-area');
  assert.equal(page.map.snapshot().camera, null);
  area.fire('pointerdown', {pointerId: 1, button: 0, clientX: 500, clientY: 350});
  area.fire('pointermove', {pointerId: 1, clientX: 600, clientY: 400, preventDefault() {}});
  area.fire('pointerup', {pointerId: 1});
  const camera = page.map.snapshot().camera;
  assert.ok(camera, 'the fitted camera retains its translation after release');
  assert.equal(camera.k, 1);
  assert.equal(page.map.snapshot().view, 'system');
  let swallowed = false;
  area.fire('click', {stopPropagation() {swallowed = true;}, preventDefault() {}});
  assert.ok(swallowed, 'a completed drag cannot accidentally choose a node');
  page.section.fire('explorer:fit', { detail: {} });
  assert.equal(page.map.snapshot().camera, null);
});

test('a choice tells the explorer frame, an arrival does not; the trail and Escape step back up', async () => {
  const scene = typedScene(), id = mostConnected(scene);
  const page = await mount({ scene, explorer: true, areaWidth: 1037, areaHeight: 730, hash: '#map=' + encodeURIComponent(id) });
  assert.equal(page.map.snapshot().component, id);
  assert.ok(!page.dispatched.includes('explorer:selected'), 'arriving at an address brings nothing forward');
  page.map.select('area:formal_math_and_proof');
  assert.ok(page.dispatched.includes('explorer:selected'));
  page.map.select(id);
  page.press(page.headEl.querySelector('.sm-trail').querySelectorAll('.sm-crumbs__go')[1]);
  assert.equal(page.map.snapshot().view, 'family');
  page.key('Escape');
  assert.equal(page.map.snapshot().view, 'system');
  assert.ok(!page.headEl.classList.contains('is-collapsed'));
  assert.ok(page.headEl.querySelector('.sm-trail').hidden);
});

test('the landing keeps its ways into the full map on the drawing’s choice', async () => {
  const scene = typedScene(), id = mostConnected(scene);
  const page = await mount({ scene });
  const href = () => page.expandLinks[0].getAttribute('href');
  assert.equal(href(), 'docs/system-map.html');
  page.map.select(id);
  assert.equal(href(), 'docs/system-map.html#map=' + encodeURIComponent(id));
  page.map.select('area:formal_math_and_proof');
  assert.equal(href(), 'docs/system-map.html#map=' + encodeURIComponent('family:formal_math_and_proof'));
  page.map.select('doctrine:P-3');
  assert.equal(href(), 'docs/system-map.html#map=' + encodeURIComponent('doctrine:P-3'));
  page.key('Escape');
  assert.equal(href(), 'docs/system-map.html#map=doctrine', 'stepping back follows too');
  page.map.select(null);
  assert.equal(href(), 'docs/system-map.html');
});

test('the source keeps its promises: no canvas, no ticking timers, no inline styles, no watch words, no em dashes', () => {
  assert.doesNotMatch(source, /getContext\(|<canvas/, 'every word is real text');
  assert.doesNotMatch(source, /setInterval/, 'nothing ticks on a timer');
  assert.doesNotMatch(source, /setAttribute\(\s*'style'/, 'the site’s policy forbids inline styles');
  assert.doesNotMatch(source, /\b(?:gear|escapement|bezel|caseback|chronograph|jewel)\b/i, 'no watch words in the code or its comments');
  // The strings it writes, read from the code without its comments and
  // without the one pattern that exists to catch a dash in authored prose.
  const code = source.replace(/\/\*[\s\S]*?\*\//g, '').replace(/^\s*\/\/.*$/gm, '').replace(/var UNPLAIN = [^\n]*\n/, '');
  const strings = code.match(/'(?:[^'\\\n]|\\.)*'/g) || [];
  assert.ok(strings.length > 200);
  strings.forEach(s => assert.doesNotMatch(s, /—|\\u2014/, s));
  assert.doesNotMatch(source, /links_note/, 'the engineer’s note is never read');
  assert.doesNotMatch(source, /whose code checks it|Point at a component|works with\b/);
});

/* ---- The necklace, the rays, the fibres, the weave ----------------------------- */
const PINNED = ['AX-12', 'AX-5', 'AX-8', 'AX-6', 'AX-10', 'AX-4', 'AX-11', 'AX-9', 'AX-3', 'AX-2', 'AX-7', 'AX-1'];
// The published doctrine manifest, when the checkout has one.
function publishedDoctrine() {
  try { return JSON.parse(readFileSync(DOCTRINE_PATH, 'utf8')); } catch (e) { return null; }
}
test('the doctrine is a necklace in the pinned order: no glyph under ten pixels, none touching another, nothing near the centre', async () => {
  const scene = liveScene(), published = publishedDoctrine();
  if (published) {
    // The published doctrine, at the smallest landing size, in the order searched offline for it.
    const real = await mount({ scene, doctrine: published, areaWidth: 820 });
    const r = real.map.snapshot().ring.core;
    assert.deepEqual(plain(r.order), PINNED);
    assert.equal(r.pinned, true);
    assert.ok(r.glyphGap > 0, 'no two glyphs touch: ' + r.glyphGap);
    assert.ok(r.smallest >= 10);
  }
  // A doctrine tied differently (the fixture) still lays out with nothing touching.
  const doctrine = doctrineFor(scene);
  const page = await mount({ scene, doctrine, areaWidth: 820 });
  const k = page.map.snapshot().ring.core;
  assert.ok(k.smallest >= 10, 'every glyph at least ten pixels');
  assert.ok(k.glyphGap > 0, 'no two glyphs touch: ' + k.glyphGap);
  const f = page.map.snapshot().ring.frame;
  assert.ok(k.nearest > (f.label.x1 - f.label.x0) / 2 - 8, 'the doctrine’s own lines keep clear of its name');
  // A rule tied to one axiom is that axiom's satellite; one tied to several stands on the necklace.
  doctrine.principles.concat(doctrine.anti_principles).forEach(r => {
    const on = r.rests_on || r.guards, n = page.root.querySelector('.sm-node--rule[data-sm-key="rule:' + r.id + '"]');
    assert.ok(n.classList.contains(on.length === 1 ? 'sm-node--sat' : 'sm-node--bridge'), r.id);
  });
  // A changed doctrine is ordered afresh, not forced into an order that no longer names it.
  const fewer = doctrineFor(scene);
  fewer.axioms = fewer.axioms.slice(0, 11);
  const ids = new Set(fewer.axioms.map(a => a.id));
  fewer.principles.forEach(p => { p.rests_on = p.rests_on.filter(a => ids.has(a)); if (!p.rests_on.length) p.rests_on = ['AX-1']; });
  fewer.anti_principles.forEach(g => { g.guards = g.guards.filter(a => ids.has(a)); if (!g.guards.length) g.guards = ['AX-1']; });
  const other = await mount({ scene, doctrine: fewer, areaWidth: 820 });
  assert.equal(other.map.snapshot().ring.core.pinned, false);
  assert.equal(other.map.snapshot().ring.core.order.length, 11);
});

// The points of a drawn line, from its path data (straight runs, sampled finely).
const pointsOf = d => [...d.matchAll(/[ML]\s*(-?[\d.]+)[ ,](-?[\d.]+)/g)].map(m => [+m[1], +m[2]]);
test('a rule line never travels round the core and never passes behind the centre’s name', async () => {
  const scene = liveScene(), doctrine = doctrineFor(scene);
  const page = await mount({ scene, doctrine, areaWidth: 820 });
  const views = [busiest(scene), isolated(scene), compNodes(scene)[40].id, 'doctrine:P-3', 'doctrine:AX-5', 'doctrine:P-15'].filter(Boolean);
  let rays = 0, most = 0;
  for (const v of views) {
    page.map.select(v);
    const f = page.map.snapshot().ring.frame;
    page.root.querySelectorAll('.sm-rline').forEach(w => {
      const pts = pointsOf(w.getAttribute('d'));
      rays++;
      pts.forEach(([x, y]) => assert.ok(!(x > f.label.x0 && x < f.label.x1 && y > f.label.y0 && y < f.label.y1), 'behind the name: ' + v));
      // Round the outside of the core, a line travels a quarter of the way at most.
      let travel = 0;
      for (let i = 1; i < pts.length; i++) {
        const [a, b] = [pts[i - 1], pts[i]];
        if (Math.hypot(a[0] - f.cx, a[1] - f.cy) < f.gate || Math.hypot(b[0] - f.cx, b[1] - f.cy) < f.gate) continue;
        let d = Math.atan2(b[1] - f.cy, b[0] - f.cx) - Math.atan2(a[1] - f.cy, a[0] - f.cx);
        d = Math.atan2(Math.sin(d), Math.cos(d));
        travel += Math.abs(d);
      }
      most = Math.max(most, travel * 180 / Math.PI);
    });
  }
  assert.ok(rays > 30);
  assert.ok(most < 90, 'the furthest a rule line travels round the core: ' + most.toFixed(1) + ' degrees');
});

test('fibres are tapered filled outlines, each kind its own texture, and the weave cuts the line beneath', async () => {
  const scene = typedScene();
  const page = await mount({ scene, areaWidth: 820 });
  const subpaths = el => (el.getAttribute('d').match(/M/g) || []).length;
  const mean = kind => { const els = page.root.querySelectorAll('.sm-fibre--' + kind); return els.reduce((t, e) => t + subpaths(e), 0) / els.length; };
  page.root.querySelectorAll('.sm-fibre').forEach(el => assert.match(el.getAttribute('d'), /Z/));
  assert.ok(mean('reads') > mean('runs') + 2, 'reading saved results is dashed');
  assert.ok(mean('checks') > mean('reads'), 'checking copied files is dotted');
  // A rule's lines cross the fibres at rest; where they do, the fibre beneath
  // is cut (counted on the solid fibres, whose only gaps are the weave's).
  const solid = () => page.root.querySelectorAll('.sm-fibre--runs').reduce((t, e) => t + subpaths(e), 0);
  const before = solid();
  page.map.select('doctrine:P-2');
  const s = page.map.snapshot();
  assert.ok(s.weave && s.weave.crossings > 0, 'the rule’s lines cross the fibres');
  assert.ok(solid() > before, 'a lit line passes over a stray fibre, which takes a gap');
  page.map.select(null);
  assert.equal(solid(), before, 'back at rest every fibre is whole');
});

/* ---- Enforcement shown by tests --------------------------------------------------- */
test('enforcement from tests: a strong frame where a test shows the rule, an open one where it checks a part, the card’s other names listed only', async () => {
  const scene = liveScene(), doctrine = doctrineFor(scene), comps = compNodes(scene).map(n => n.id);
  [...doctrine.axioms, ...doctrine.principles, ...doctrine.anti_principles].forEach(r => {
    r.named_in_card = r.enforced_in.slice(); r.enforced_in = []; r.partly_enforced_in = [];
  });
  const p = doctrine.principles[2], [full, part, card] = [comps[5], comps[9], comps[13]];
  p.enforced_in = [full]; p.partly_enforced_in = [part]; p.named_in_card = [full, part, card];
  const page = await mount({ scene, doctrine });
  assert.equal(page.root.querySelectorAll('.sm-cap').filter(c => !c.classList.contains('sm-cap--part')).length, 1, 'one strong mark on the rim');
  assert.equal(page.root.querySelectorAll('.sm-cap--part').length, 1, 'one open mark of the same family');
  page.map.select('doctrine:P-3');
  const s = page.map.snapshot();
  assert.deepEqual(plain(s.lit.reticles).sort(), ['comp:' + full, 'rule:P-3'].sort());
  assert.deepEqual(plain(s.lit.open), ['comp:' + part]);
  const citing = doctrine.components.filter(r => r.governed_by.includes('P-3')).map(r => r.id);
  const lines = page.root.querySelectorAll('.sm-rline').map(w => w.getAttribute('data-to').slice(5));
  assert.deepEqual(lines.sort(), [...new Set([...citing, full, part])].sort(), 'a name only on the card is never drawn');
  const col = page.textOf(page.panel());
  assert.match(col, /Enforced in · 1/);
  assert.match(col, /Partly checked in · 1/);
  assert.match(col, /Named in its doctrine card, not yet demonstrated by a test · 1/);
  const key = page.textOf(page.keySlot);
  assert.match(key, /Enforced here/);
  assert.match(key, /Partly checked here/);
  assert.doesNotMatch(key, /by its card/);
  page.map.select(card);
  assert.doesNotMatch(page.textOf(page.panel()), /Enforced here|Partly checked here|Named in its doctrine card/, 'the card’s name is listed only with the rule');
  page.map.select('doctrine');
  assert.match(page.textOf(page.panel()), /A rule is marked enforced in a component only where a test shows it\./);
});

/* ---- The column fits ----------------------------------------------------------------- */
test('the column shows the first eight of a long list with the rest on request, and never says more below', async () => {
  const scene = liveScene();
  const page = await mount({ scene });
  const id = busiest(scene);
  page.map.select(id);
  const block = page.panel().querySelectorAll('.sc__block').find(b => /Listed as related/.test(page.textOf(b)));
  const total = +/Listed as related · (\d+)/.exec(page.textOf(block))[1];
  assert.ok(total > 9);
  assert.equal(block.querySelectorAll('.sc__li').length, 8);
  const all = block.querySelector('.sc__all');
  assert.match(all.textContent, new RegExp('Show all ' + total));
  page.press(all);
  const open = page.panel().querySelectorAll('.sc__block').find(b => /Listed as related/.test(page.textOf(b)));
  assert.equal(open.querySelectorAll('.sc__li').length, total);
  assert.doesNotMatch(page.textOf(page.host), /More below/);
  assert.equal(page.host.querySelectorAll('.sc__more').length, 0);
  // A rule's citing families run on while none is open; one opened, they stand one to a row.
  const doc = await mount({ scene, doctrine: doctrineFor(scene) });
  const cited = doctrineFor(scene).principles.find(p => doctrineFor(scene).components.some(r => r.governed_by.includes(p.id)));
  doc.map.select('doctrine:' + cited.id);
  const groupsOf = () => doc.panel().querySelector('.sc__group-btn').parentNode.parentNode;
  assert.ok(groupsOf().classList.contains('sc__list--flow'), 'the families run on');
  doc.press(doc.panel().querySelector('.sc__group-btn'));
  assert.ok(!groupsOf().classList.contains('sc__list--flow'), 'one opened, one to a row');
  assert.ok(doc.panel().querySelectorAll('.sc__list--inner .sc__li').length > 0, 'its components beneath it');
});

/* ---- Frames side by side ------------------------------------------------------------ */
test('frames round neighbouring marks never touch, and a framed name is framed as its mark is', async () => {
  const scene = liveScene(), doctrine = doctrineFor(scene), fam = famOf(scene);
  [...doctrine.axioms, ...doctrine.principles, ...doctrine.anti_principles].forEach(r => {
    r.named_in_card = r.enforced_in.slice(); r.enforced_in = []; r.partly_enforced_in = [];
  });
  // A whole small family side by side: three shown enforcing a rule, two checking part of it.
  const sizes = {};
  Object.values(fam).forEach(f => { sizes[f] = (sizes[f] || 0) + 1; });
  const small = Object.keys(sizes).filter(f => sizes[f] >= 5).sort((a, b) => sizes[a] - sizes[b])[0];
  const members = compNodes(scene).map(n => n.id).filter(id => fam[id] === small).slice(0, 5);
  const p = doctrine.principles[2];
  p.enforced_in = members.slice(0, 3); p.partly_enforced_in = members.slice(3);
  const page = await mount({ scene, doctrine, areaWidth: 820 });
  page.map.select('doctrine:' + p.id);
  const frames = page.root.querySelectorAll('.sm-reticle--rim').map(path => {
    const t = /translate\((-?[\d.]+) (-?[\d.]+)\)/.exec(path.parentNode.getAttribute('transform'));
    const xs = [...path.getAttribute('d').matchAll(/[MH]\s*(-?[\d.]+)/g)].map(m => Math.abs(+m[1]));
    return { x: +t[1], y: +t[2], half: Math.max(...xs) };
  });
  assert.equal(frames.length, 5);
  let closest = Infinity;
  frames.forEach((a, i) => frames.forEach((b, j) => {
    if (j <= i) return;
    const d = Math.hypot(a.x - b.x, a.y - b.y);
    closest = Math.min(closest, d);
    assert.ok(d >= a.half + b.half + 1, 'two frames touch: ' + d.toFixed(1) + ' apart');
  }));
  assert.ok(closest < 23, 'the case is a crowded one');
  const framed = cls => page.root.querySelectorAll('.sm-plate.' + cls).map(g => g.getAttribute('data-sm-plate').slice(5));
  framed('sm-plate--full').forEach(id => assert.ok(p.enforced_in.includes(id)));
  framed('sm-plate--part').forEach(id => assert.ok(p.partly_enforced_in.includes(id)));
  assert.ok(framed('sm-plate--full').length + framed('sm-plate--part').length > 0, 'a named plate carries its frame');
});

/* ---- The scene derived from the code ------------------------------------------- */
// The checkout's own scene when it is derived from the code; otherwise the
// typed fixture with one component reading the saved results of twenty-one
// others across three families, as the regenerated scene has one.
function codeScene() {
  const json = detailedScene();
  if (codeEdges(json).length) return json;
  const typed = typedScene(), fam = famOf(typed), ids = compNodes(typed).map(n => n.id), hub = ids[0];
  const others = [...new Set(ids.map(id => fam[id]))].filter(f => f !== fam[hub]).slice(0, 3);
  others.forEach(f => ids.filter(id => fam[id] === f).slice(0, 7).forEach(id => {
    if (typed.scene.edges.some(e => e.source === hub && e.target === id)) return;
    typed.scene.edges.push({ id: 'edge:wire:hub:' + id, source: hub, target: id, relation: 'reads_results_of',
      evidence: [{ path: 'src/hub_reader.py', lines: [40, 42], role: 'opens_file' }] });
  }));
  typed.edge_semantics = { explicit_wire_relation: 'derived_from_code' };
  const ins = typed.scene.inspectors['inspector:' + hub];
  if (ins) ins.source_links = [{ label: 'Source', url: 'https://github.com/example/repository/blob/main/src/hub_reader.py' }];
  return typed;
}
// The component with the most code connections of one kind, from its side.
function widestFan(scene) {
  const tally = {};
  codeEdges(scene).forEach(e => { const k = e.source + '|' + e.relation; tally[k] = (tally[k] || 0) + 1; });
  const [hub, relation] = Object.entries(tally).sort((x, y) => y[1] - x[1] || (x[0] < y[0] ? -1 : 1))[0][0].split('|');
  return { hub, relation, edges: codeEdges(scene).filter(e => e.source === hub && e.relation === relation) };
}
test('one component reaching many in other families gathers them, family by family, into a few ribbons that part at each family', async () => {
  const scene = codeScene(), fam = famOf(scene), fan = widestFan(scene);
  const page = await mount({ scene, areaWidth: 820 });
  const s = page.map.snapshot(), per = {};
  fan.edges.forEach(e => { if (fam[e.target] !== fam[fan.hub]) per[fam[e.target]] = (per[fam[e.target]] || 0) + 1; });
  const wanted = Object.entries(per).filter(([, n]) => n >= 2);
  assert.ok(wanted.length >= 2 && wanted.some(([, n]) => n >= 5), 'the fan is a wide one');
  const ribbons = plain(s.ring.sheaves).filter(r => r.from === 'comp:' + fan.hub && r.role === 'out');
  // Into each family it reaches five times or more, one ribbon carries them
  // all; it has no ribbon anywhere it reaches once.
  wanted.filter(([, n]) => n >= 5).forEach(([f, n]) => assert.deepEqual(ribbons.filter(r => r.family === f).map(r => r.links), [n], f));
  ribbons.forEach(r => assert.ok(r.links >= 2 && r.links <= per[r.family]));
  assert.ok(ribbons.length <= wanted.length, 'a few ribbons, not a hair for each link');
  // At rest each ribbon is one shape, and each link its own parting fibre.
  const trunks = page.root.querySelectorAll('.sm-fibre.is-trunk').filter(t => t.getAttribute('data-from') === 'comp:' + fan.hub);
  assert.equal(trunks.length, ribbons.length);
  trunks.forEach(t => assert.match(t.getAttribute('d'), /Z/));
  // Chosen, it lights each ribbon once and one wire for each of its links.
  page.map.select(fan.hub);
  const touching = codeEdges(scene).filter(e => e.source === fan.hub || e.target === fan.hub);
  assert.equal(page.root.querySelectorAll('.sm-route.sm-wire').length, new Set(touching.map(e => e.source + '>' + e.target + '>' + e.relation)).size);
  assert.ok(page.root.querySelectorAll('.sm-route.is-trunk').length >= ribbons.length);
  // One of the far components chosen alone lights its own whole route, the
  // ribbon it shares staying at rest beneath.
  const far = fan.edges.find(e => (per[fam[e.target]] || 0) >= 2).target;
  page.map.select(far);
  assert.equal(page.root.querySelectorAll('.sm-route.is-trunk').filter(t => t.getAttribute('data-from') === 'comp:' + fan.hub).length, 0);
  assert.ok(page.root.querySelectorAll('.sm-fibre.is-trunk').some(t => t.getAttribute('data-from') === 'comp:' + fan.hub && !t.classList.contains('is-under')));
});
test('the key says where the red lines come from and how many components have none; the caption and the families say so too', async () => {
  const scene = codeScene(), edges = codeEdges(scene), comps = compNodes(scene), fam = famOf(scene);
  const page = await mount({ scene, doctrine: doctrineFor(scene) });
  const none = comps.filter(n => !edges.some(e => e.source === n.id || e.target === n.id));
  assert.ok(none.length > 0);
  assert.match(page.map.snapshot().caption, new RegExp('^' + comps.length + ' components round the rim in seven families, ' + none.length +
    ' of them with no code connection, and the doctrine at the centre\\. Select any of them to light what it touches\\.$'));
  page.press(page.keySlot.querySelector('.sm-key__more'));
  const key = page.textOf(page.keySlot);
  assert.match(key, /Red lines are derived from the code: each one rests on the place in the code where one component runs another, reads its saved results or checks its copied files\./);
  assert.match(key, new RegExp(none.length + ' of the ' + comps.length + ' components ' + (none.length === 1 ? 'has' : 'have') + ' none\\.'));
  assert.match(key, /One component’s lines to several in one family travel as one ribbon/);
  // A family with some components and none of their code connected says how many.
  const f = Object.values(fam).find(k => none.some(n => fam[n.id] === k) && comps.some(n => fam[n.id] === k && !none.includes(n)));
  page.map.select('area:' + f);
  const count = none.filter(n => fam[n.id] === f).length, of = comps.filter(n => fam[n.id] === f).length;
  assert.match(page.textOf(page.panel()), new RegExp(count + ' of its ' + of + ' components ' + (count === 1 ? 'has' : 'have') + ' none\\.'));
});
test('a component with no code connection says so plainly; each code connection links to the line of code that makes it', async () => {
  const scene = codeScene(), edges = codeEdges(scene);
  const page = await mount({ scene, doctrine: doctrineFor(scene) });
  const lone = compNodes(scene).map(n => n.id).find(id => !edges.some(e => e.source === id || e.target === id));
  page.map.select(lone);
  assert.match(page.map.snapshot().caption, /^No code connections to other components; azure lines to the rules its paper module cites\.$/);
  assert.match(page.textOf(page.panel()), /No code connections\. Its code does not run, read or check another component, and no other component’s code runs, reads or checks it\./);
  const fan = widestFan(scene);
  page.map.select(fan.hub);
  const links = page.panel().querySelectorAll('.sc__code');
  assert.ok(links.length > 0, 'a link to the code beside each connection');
  links.forEach(a => {
    assert.equal(a.textContent, 'Code');
    // A whole-file link, never a line anchor: the published repository can lag
    // the source the evidence lines were read from.
    assert.match(a.getAttribute('href'), /^https:\/\/github\.com\/[^/]+\/[^/]+\/blob\/[^/]+\/[^#]+\.py$/);
    assert.match(a.getAttribute('aria-label'), /^The code file joining /);
  });
  assert.match(page.textOf(page.panel()), /Each is derived from the code; Code opens the file that makes it\./);
});
