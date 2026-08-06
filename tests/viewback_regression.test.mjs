// Behavioral regression harness for the Microcosm "Back to where you were"
// (viewback) exact-return trail in ../assets/docs.js.
//
// WHY THIS SHAPE: docs.js is one outer IIFE wrapping defensively-guarded module
// IIFEs; every sibling module bails at `var x = document.querySelector(...); if
// (!x) return;`, which is exactly why the shipped file runs with zero console
// errors on the bare landing page. So we load the REAL shipped file into a
// node:vm context backed by a minimal-but-faithful DOM / sessionStorage /
// location / performance shim and only viewState() meaningfully executes. We
// then drive it across SIMULATED page loads (persistent sessionStorage + a fresh
// vm context per "page" + dispatched pagehide/pageshow) so the assertions hit
// the actual reconcile / push / pop / snapshot / restore / BFCache code paths —
// not a re-implementation and not a string match. No browser, no Playwright, no
// npm install: node:test + node:vm + node:fs only.
//
// Run from repo root:
//   node --test sites/microcosm/tests/
//   node sites/microcosm/tests/viewback_regression.test.mjs
//
// Guards CAP cap_quick_add_an_automated_regression_guard_for_th_a25d1b843628 and
// the reader-control-plane exact-return matrix: landing participation,
// direction-aware reconcile (forward-click keeps the trail; Back/Forward
// truncates; reload strips only the self-push), BFCache pageshow recompute,
// scroll + focus + open-card restore, and sessionStorage-off safety.

import { test } from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const HERE = dirname(fileURLToPath(import.meta.url));
const ASSETS = join(HERE, '..', 'assets');
// MICROCOSM_DOCS_JS lets a negative-control run point the harness at a mutated
// copy to prove the guard actually fails on a real regression. Default: shipped.
const DOCS_JS = process.env.MICROCOSM_DOCS_JS || join(ASSETS, 'docs.js');
const STYLE_CSS = join(ASSETS, 'style.css');
const ART_JS = join(ASSETS, 'art.js');
const SOURCE = readFileSync(DOCS_JS, 'utf8');
const STYLE_SOURCE = readFileSync(STYLE_CSS, 'utf8');
const ART_SOURCE = readFileSync(ART_JS, 'utf8');
const ORIGIN = 'https://microcosm.example';

// ── Minimal DOM ──────────────────────────────────────────────────────────────

function makeClassList(el) {
  const parse = () => el.className.split(/\s+/).filter(Boolean);
  const join = (set) => { el.className = [...set].join(' '); };
  return {
    add(...cs) { const s = new Set(parse()); cs.forEach((c) => s.add(c)); join(s); },
    remove(...cs) { const s = new Set(parse()); cs.forEach((c) => s.delete(c)); join(s); },
    toggle(c, force) {
      const s = new Set(parse());
      const want = force === undefined ? !s.has(c) : !!force;
      if (want) s.add(c); else s.delete(c);
      join(s);
      return want;
    },
    contains(c) { return parse().includes(c); },
  };
}

function makeEl(tag) {
  const el = {
    tagName: String(tag || '').toUpperCase(),
    nodeType: tag === '#text' ? 3 : 1,
    id: '',
    children: [],
    parentNode: null,
    parentElement: null,
    className: '',
    style: {},
    type: '',
    value: '',
    open: false,
    hidden: false,
    innerHTML: '',
    _attrs: {},
    _text: '',
    _listeners: {},
    _focused: false,
    _focusPreventScroll: false,
    _docTop: null,
    _left: 0,
    _width: 0,
    _height: 0,
    offsetWidth: 0,
    offsetHeight: 0,
    _window: null,
    setAttribute(k, v) {
      this._attrs[k] = String(v);
      if (k === 'id') this.id = String(v);
      if (k === 'class') this.className = String(v);
      if (k === 'hidden') this.hidden = true;
    },
    getAttribute(k) { return Object.prototype.hasOwnProperty.call(this._attrs, k) ? this._attrs[k] : null; },
    removeAttribute(k) { delete this._attrs[k]; if (k === 'hidden') this.hidden = false; },
    appendChild(c) { c.parentNode = this; c.parentElement = this.nodeType === 1 ? this : null; this.children.push(c); return c; },
    removeChild(c) { const i = this.children.indexOf(c); if (i >= 0) this.children.splice(i, 1); c.parentNode = null; c.parentElement = null; return c; },
    addEventListener(type, fn) { (this._listeners[type] || (this._listeners[type] = [])).push(fn); },
    removeEventListener(type, fn) { const a = this._listeners[type]; if (a) { const i = a.indexOf(fn); if (i >= 0) a.splice(i, 1); } },
    dispatch(type, ev) {
      const event = ev || {};
      if (!event.type) event.type = type;
      (this._listeners[type] || []).slice().forEach((fn) => fn(event));
    },
    focus(opts) { this._focused = true; this._focusPreventScroll = !!(opts && opts.preventScroll); },
    scrollIntoView() {},
    getBoundingClientRect() {
      const y = this._window ? this._window.pageYOffset || 0 : 0;
      const docTop = this._docTop == null ? y : this._docTop;
      const top = docTop - y;
      const left = this._left || 0;
      const width = this._width || 0;
      return {
        top,
        bottom: top + (this._height || 0),
        height: this._height || 0,
        left,
        right: left + width,
        width,
      };
    },
    querySelector(sel) {
      return queryAll(this, sel)[0] || null;
    },
    querySelectorAll(sel) { return queryAll(this, sel); },
    contains(node) {
      let current = node;
      while (current) {
        if (current === this) return true;
        current = current.parentElement || current.parentNode;
      }
      return false;
    },
    closest(sel) {
      let node = this;
      while (node && node.nodeType === 1) {
        if (matchesSelectorList(node, sel)) return node;
        node = node.parentElement || node.parentNode;
      }
      return null;
    },
    cloneNode(deep) {
      const clone = makeEl(this.nodeType === 3 ? '#text' : this.tagName.toLowerCase());
      clone.id = this.id;
      clone.className = this.className;
      clone.type = this.type;
      clone.value = this.value;
      clone.open = this.open;
      clone.hidden = this.hidden;
      clone.innerHTML = this.innerHTML;
      clone._attrs = { ...this._attrs };
      clone._text = this._text;
      clone._docTop = this._docTop;
      clone._left = this._left;
      clone._width = this._width;
      clone._height = this._height;
      if (deep) this.children.forEach((child) => clone.appendChild(child.cloneNode(true)));
      return clone;
    },
    select() {},
    setSelectionRange() {},
    get textContent() {
      if (this.children.length) return this.children.map((c) => c.textContent).join('');
      return this._text;
    },
    set textContent(v) { this._text = String(v); this.children = []; },
  };
  el.classList = makeClassList(el);
  return el;
}

function makeLink(href, id) {
  const a = makeEl('a');
  a.setAttribute('href', href);
  if (id) a.id = id;
  return a;
}

function makeDetails(id) {
  const d = makeEl('details');
  d.id = id;
  return d;
}

function walk(root, pred) {
  const stack = [...root.children];
  while (stack.length) {
    const n = stack.shift();
    if (pred(n)) return n;
    if (n.children) stack.push(...n.children);
  }
  return null;
}

function walkAll(root) {
  const out = [];
  const stack = [...(root.children || [])];
  while (stack.length) {
    const n = stack.shift();
    out.push(n);
    if (n.children) stack.push(...n.children);
  }
  return out;
}

function attrValue(node, name) {
  if (name === 'id') return node.id || node.getAttribute('id');
  if (name === 'class') return node.className || node.getAttribute('class');
  if (name === 'open') return node.open ? '' : null;
  if (name === 'hidden') return node.hidden ? '' : null;
  return node.getAttribute(name);
}

function matchesSimpleSelector(node, selector) {
  if (!node || node.nodeType !== 1) return false;
  const sel = String(selector || '').trim();
  if (!sel) return false;
  const tag = sel.match(/^[a-z][a-z0-9-]*/i);
  if (tag && node.tagName !== tag[0].toUpperCase()) return false;
  const classes = [...sel.matchAll(/\.([A-Za-z0-9_-]+)/g)].map((m) => m[1]);
  for (const cls of classes) {
    if (!node.classList || !node.classList.contains(cls)) return false;
  }
  const attrs = [...sel.matchAll(/\[([^\]=\s]+)(?:=["']?([^\]"']+)["']?)?\]/g)];
  for (const attr of attrs) {
    const actual = attrValue(node, attr[1]);
    if (actual == null) return false;
    if (attr[2] != null && actual !== attr[2]) return false;
  }
  return true;
}

function matchesSelectorList(node, selector) {
  return String(selector || '').split(',').some((part) => matchesCompoundSelector(node, part.trim()));
}

function matchesCompoundSelector(node, selector) {
  const parts = String(selector || '').trim().split(/\s+/).filter(Boolean);
  if (!parts.length) return false;
  if (!matchesSimpleSelector(node, parts[parts.length - 1])) return false;
  let ancestor = node.parentElement || node.parentNode;
  for (let i = parts.length - 2; i >= 0; i -= 1) {
    while (ancestor && !matchesSimpleSelector(ancestor, parts[i])) {
      ancestor = ancestor.parentElement || ancestor.parentNode;
    }
    if (!ancestor) return false;
    ancestor = ancestor.parentElement || ancestor.parentNode;
  }
  return true;
}

function queryAll(root, selector) {
  const selectors = String(selector || '').split(',').map((s) => s.trim()).filter(Boolean);
  const results = [];
  for (const node of walkAll(root)) {
    if (selectors.some((sel) => matchesCompoundSelector(node, sel))) results.push(node);
  }
  return results;
}

function countViewback(body) {
  let n = 0;
  const stack = [...body.children];
  while (stack.length) {
    const el = stack.shift();
    if (el.classList && el.classList.contains('viewback')) n += 1;
    if (el.children) stack.push(...el.children);
  }
  return n;
}

// ── Per-tab session (sessionStorage persists across same-tab navigations) ──────

function makeStore(blocked) {
  const map = new Map();
  return {
    getItem(k) { return map.has(k) ? map.get(k) : null; },
    setItem(k, v) { if (blocked) throw new Error('storage blocked'); map.set(k, String(v)); },
    removeItem(k) { if (blocked) throw new Error('storage blocked'); map.delete(k); },
    _map: map,
  };
}

function makeTab(opts = {}) {
  return { store: makeStore(opts.blockedStorage), pendingHref: null, lastScrollTo: undefined, scrollToCalls: [] };
}

// Load one "page" of the tab: build a fresh window/document/location context,
// run the real docs.js, and return a handle to drive it.
function loadPage(tab, page) {
  const body = makeEl('body');
  const head = makeEl('head');
  const docEl = makeEl('html');
  docEl.scrollTop = 0;
  (page.bodyChildren || []).forEach((child) => body.appendChild(child));

  const byId = {};
  (page.openDetails || []).forEach((d) => { byId[d.id] = d; });
  (page.byId || []).forEach((el) => { byId[el.id] = el; });
  const links = page.links || [];

  const docListeners = {};
  const doc = {
    title: page.title || '',
    readyState: 'complete',
    documentElement: docEl,
    head,
    body,
    activeElement: page.active || null,
    createElement: (t) => makeEl(t),
    createTextNode: (t) => { const n = makeEl('#text'); n._text = String(t); return n; },
    getElementById(id) { return Object.prototype.hasOwnProperty.call(byId, id) ? byId[id] : null; },
    getElementsByTagName(tag) { return String(tag).toLowerCase() === 'a' ? links : []; },
    querySelector(sel) {
      return queryAll(body, sel)[0] || queryAll(head, sel)[0] || null;
    },
    querySelectorAll(sel) {
      if (sel === 'details[open][id]') return (page.openDetails || []).filter((d) => d.open && d.id);
      if (sel === '[data-reader-stage="diagram"], .pm-diagram') return page.diagrams || [];
      return queryAll(body, sel);
    },
    elementFromPoint() { return page.hitTarget || null; },
    addEventListener(type, fn) { (docListeners[type] || (docListeners[type] = [])).push(fn); },
    removeEventListener(type, fn) {
      const listeners = docListeners[type];
      if (!listeners) return;
      const index = listeners.indexOf(fn);
      if (index >= 0) listeners.splice(index, 1);
    },
    dispatch(type, ev) {
      const event = ev || {};
      if (!event.type) event.type = type;
      (docListeners[type] || []).slice().forEach((fn) => fn(event));
    },
    execCommand: page.execCommand || (() => false),
  };

  const winListeners = {};
  const loc = {
    pathname: page.path,
    search: page.search || '',
    hash: page.hash || '',
    origin: ORIGIN,
    get href() { return ORIGIN + this.pathname + this.search + this.hash; },
    set href(v) { tab.pendingHref = String(v); },
  };
  const perf = {
    getEntriesByType(t) { return t === 'navigation' ? [{ type: page.navType || 'navigate' }] : []; },
    navigation: { type: page.navType === 'back_forward' ? 2 : page.navType === 'reload' ? 1 : 0 },
  };
  const win = {
    sessionStorage: tab.store,
    location: loc,
    pageYOffset: page.scrollY || 0,
    requestAnimationFrame(fn) { try { fn(); } catch (e) {} return 1; },
    setTimeout(fn) { try { fn(); } catch (e) {} return 0; },
    clearTimeout() {},
    scrollTo(x, y) { tab.lastScrollTo = y; tab.scrollToCalls.push(y); this.pageYOffset = y; docEl.scrollTop = y; },
    addEventListener(type, fn) { (winListeners[type] || (winListeners[type] = [])).push(fn); },
    removeEventListener() {},
    performance: perf,
    history: { pushState() {}, replaceState() {} },
    matchMedia() { return { matches: false, addEventListener() {}, removeEventListener() {}, addListener() {}, removeListener() {} }; },
    getComputedStyle() { return { getPropertyValue() { return ''; } }; },
    innerWidth: 1024,
    innerHeight: 768,
  };
  Object.assign(win, page.windowGlobals || {});
  win.self = win;
  function bindWindow(el) {
    if (!el || el.nodeType !== 1) return;
    el._window = win;
    (el.children || []).forEach(bindWindow);
  }
  [body, head, docEl].concat(page.bodyChildren || [], page.openDetails || [], page.byId || [], links).forEach(bindWindow);

  const sandbox = {
    window: win,
    document: doc,
    location: loc,
    performance: perf,
    navigator: { clipboard: page.clipboard === undefined ? null : page.clipboard, userAgent: 'node-harness' },
    console: { log() {}, warn() {}, error() {}, info() {}, debug() {} },
    setTimeout(fn) { try { fn(); } catch (e) {} return 0; },
    clearTimeout() {},
    URL,
  };
  vm.createContext(sandbox);

  let error = null;
  try {
    vm.runInContext(SOURCE, sandbox, { filename: 'docs.js' });
  } catch (e) {
    error = e;
  }

  return {
    page, doc, win, loc, body, error,
    pill() { return doc.querySelector('.viewback'); },
    pillCount() { return countViewback(body); },
    pillWhere() {
      const p = this.pill();
      if (!p) return null;
      const w = walk(p, (el) => el.classList && el.classList.contains('viewback__where'));
      return w ? w.textContent : null;
    },
    pillAria() { const p = this.pill(); return p ? p.getAttribute('aria-label') : null; },
    stack() { const s = tab.store.getItem('mc:viewstate:stack'); return s ? JSON.parse(s) : []; },
    restore() { const r = tab.store.getItem('mc:viewstate:restore'); return r ? JSON.parse(r) : null; },
    preview() { return win.__microcosmPreview; },
    firePagehide() { (winListeners.pagehide || []).forEach((fn) => fn({})); },
    firePageshow(persisted) { (winListeners.pageshow || []).forEach((fn) => fn({ persisted: !!persisted })); },
    fireScroll() { (winListeners.scroll || []).forEach((fn) => fn({})); },
    clickPill() { const p = this.pill(); if (!p) throw new Error('no pill to click'); p.dispatch('click', {}); return tab.pendingHref; },
    escapePill() { const p = this.pill(); if (!p) throw new Error('no pill'); p.dispatch('keydown', { key: 'Escape', stopPropagation() {} }); },
  };
}

// Parse a stored snapshot.url (pathname[?search][#hash]) back into parts so the
// click target can be loaded as the next page.
function partsOf(url) {
  let rest = url;
  let hash = '';
  let search = '';
  const h = rest.indexOf('#');
  if (h !== -1) { hash = rest.slice(h); rest = rest.slice(0, h); }
  const q = rest.indexOf('?');
  if (q !== -1) { search = rest.slice(q); rest = rest.slice(0, q); }
  return { path: rest, search, hash };
}

// Page descriptors used across cases.
const LANDING_LINK = () => makeLink('docs/index.html', 'cta-docs');
function landingPage(extra = {}) {
  const link = LANDING_LINK();
  return Object.assign({
    path: '/', title: 'Microcosm: a public proof instrument', navType: 'navigate',
    links: [link], active: link,
  }, extra);
}
const hubPage = (extra = {}) => Object.assign({ path: '/docs/index.html', title: 'Overview · Microcosm', navType: 'navigate' }, extra);
const archPage = (extra = {}) => Object.assign({ path: '/docs/architecture.html', title: 'How it fits together · Microcosm', navType: 'navigate' }, extra);
const areaPage = (extra = {}) => Object.assign({ path: '/docs/area-architecture.html', title: 'Architecture & navigation · Microcosm', navType: 'navigate' }, extra);
const evidencePage = (extra = {}) => Object.assign({ path: '/docs/evidence.html', title: 'Evidence · Microcosm', navType: 'navigate' }, extra);
const componentPage = (extra = {}) => Object.assign({ path: '/docs/components.html', title: 'Components · Microcosm', navType: 'navigate' }, extra);
const paperModulesPage = (extra = {}) => Object.assign({ path: '/docs/paper-modules.html', title: 'Paper modules · Microcosm', navType: 'navigate' }, extra);

// ── Cases ──────────────────────────────────────────────────────────────────

test('docs.js loads on a bare page with no thrown error (landing participation safety)', () => {
  const tab = makeTab();
  const landing = loadPage(tab, landingPage({ scrollY: 700 }));
  assert.equal(landing.error, null, 'docs.js must run end-to-end on a bare DOM');
  assert.equal(landing.pillCount(), 0, 'fresh first view shows no pill');
  assert.deepEqual(landing.stack(), [], 'fresh trail is empty');
});

test('landing enhancement work stays off the critical input path', () => {
  assert.doesNotMatch(SOURCE, /warmTermLayer|ensureLayer\(null\)/);
  assert.match(SOURCE, /var budget = 8;/);
  assert.match(SOURCE, /setTimeout\(function \(\) \{ restTimer = 0; warm\(anchor\); \}, 140\)/);
  assert.match(STYLE_SOURCE, /html\s*\{[^}]*scroll-behavior:\s*auto/s);
  assert.doesNotMatch(STYLE_SOURCE, /@view-transition|mc-ember-drift/);
  assert.doesNotMatch(ART_SOURCE, /CYCLE_MS|VEIL_MS|cycleTimer|function cycle\(/);
  assert.match(ART_SOURCE, /data-plectis-field-mode', 'still'/);
  assert.match(ART_SOURCE, /WEBGL_lose_context/);
  assert.match(ART_SOURCE, /Math\.min\(0\.75, Math\.max\(0\.5, dpr \* 0\.45\)\)/);
  assert.match(ART_SOURCE, /powerPreference: 'low-power'/);
  assert.match(ART_SOURCE, /window\.addEventListener\('scroll', onScroll, \{ passive: true \}\)/);
  assert.doesNotMatch(ART_SOURCE, /requestAnimationFrame\(frame\)/);
  assert.match(SOURCE, /if \(links\.length > 80\) return/);
  assert.match(SOURCE, /if \(\/\\\/glossary\\\.html\$\/\.test\(window\.location\.pathname/);
});

test('term first click stays local, second click drills down, and explicit actions remain', () => {
  assert.doesNotMatch(
    SOURCE,
    /function expandTip[\s\S]*?withSearchIndex\(/,
    'expanding one definition must not pull the site-wide search payload',
  );
  assert.match(SOURCE, /var tipBack = el\('button', 'term-tip__back', 'Back to page'\)/);
  assert.match(SOURCE, /tipFor === onTerm && tier === 1 && !tip\.hidden/);
  assert.match(SOURCE, /return; \/\/ second activation: allow the anchor's native navigation/);
  assert.match(STYLE_SOURCE, /\.term-tip__back\s*\{/);
  assert.match(STYLE_SOURCE, /\.viewback\s*\{[\s\S]*?position:\s*fixed;\s*left:\s*16px;\s*bottom:\s*16px/);
});

test('term activation is a real two-stage preview then native glossary navigation', () => {
  const tab = makeTab();
  const term = makeLink('glossary.html#glossary-system', 'system-link');
  term.className = 'narrative-ref--term';
  term.setAttribute('data-term', 'system');
  term.setAttribute('data-term-label', 'system');
  term.setAttribute('data-term-preview', 'A system is a set of connected parts.');
  term.setAttribute('data-term-card', 'System card: connected parts with a shared boundary.');
  term.setAttribute('data-term-rule', 'System rule: name the boundary before claiming the whole.');
  term.setAttribute('data-term-deep', 'System deep: inspect owners, edges, and receipts together.');

  const page = loadPage(tab, hubPage({ bodyChildren: [term], links: [term], active: term }));
  assert.equal(page.error, null);

  let firstPrevented = false;
  page.doc.dispatch('click', {
    target: term,
    button: 0,
    preventDefault() { firstPrevented = true; },
  });
  const tip = page.doc.querySelector('.term-tip');
  assert.equal(firstPrevented, true, 'first activation stays on the source page');
  assert.ok(tip && !tip.hidden && tip.classList.contains('is-expanded'));
  assert.equal(tip.querySelector('.term-tip__text').textContent, 'System card: connected parts with a shared boundary.');
  assert.equal(tip.querySelector('.term-tip__rule').textContent, 'System rule: name the boundary before claiming the whole.');
  assert.equal(tip.querySelector('.term-tip__deep').textContent, 'System deep: inspect owners, edges, and receipts together.');
  assert.equal(tip.querySelector('.term-tip__full').href, 'glossary.html#glossary-system');

  let secondPrevented = false;
  page.doc.dispatch('click', {
    target: term,
    button: 0,
    preventDefault() { secondPrevented = true; },
  });
  assert.equal(secondPrevented, false, 'second activation preserves native glossary navigation');
  assert.equal(tip.hidden, true, 'the source tooltip clears before navigation');
});

test('cold term activation waits for the lazy preview asset before expanding locally', () => {
  const tab = makeTab();
  const term = makeLink('glossary.html#glossary-system', 'cold-system-link');
  term.className = 'narrative-ref--term';
  term.setAttribute('data-term', 'system');

  const page = loadPage(tab, hubPage({ bodyChildren: [term], links: [term], active: term }));
  assert.equal(page.error, null);

  let firstPrevented = false;
  page.doc.dispatch('click', {
    target: term,
    button: 0,
    preventDefault() { firstPrevented = true; },
  });
  assert.equal(firstPrevented, true, 'a cold first activation stays on the source page');
  assert.equal(tab.pendingHref, null, 'the cold click does not navigate while preview data loads');

  const previewScript = page.doc.head.querySelector('script[data-term-previews]');
  assert.ok(previewScript, 'term intent requests the shared preview asset');
  page.win.__MICROCOSM_TERM_PREVIEWS__ = {
    terms: [{
      object_id: 'term:system',
      preferred_label: 'system',
      reader_preview: 'A system is a set of connected parts.',
      reader_card: 'System card: connected parts with a shared boundary.',
    }],
  };
  previewScript.dispatch('load', {});

  const tip = page.doc.querySelector('.term-tip');
  assert.ok(tip && !tip.hidden && tip.classList.contains('is-expanded'));
  assert.equal(tip.querySelector('.term-tip__text').textContent, 'System card: connected parts with a shared boundary.');
  assert.equal(tab.pendingHref, null, 'loading the preview does not change location');

  let secondPrevented = false;
  page.doc.dispatch('click', {
    target: term,
    button: 0,
    preventDefault() { secondPrevented = true; },
  });
  assert.equal(secondPrevented, false, 'the warm second activation remains native');
});

test('term preview chooses a tethered above or below placement and carries a quiet escape hint', () => {
  const tab = makeTab();
  const high = makeLink('glossary.html#glossary-high', 'high-term');
  high.className = 'narrative-ref--term';
  high.setAttribute('data-term', 'high');
  high.setAttribute('data-term-preview', 'High term preview.');
  high._docTop = 72; high._height = 20; high._left = 180; high._width = 80;
  const low = makeLink('glossary.html#glossary-low', 'low-term');
  low.className = 'narrative-ref--term';
  low.setAttribute('data-term', 'low');
  low.setAttribute('data-term-preview', 'Low term preview.');
  low._docTop = 650; low._height = 20; low._left = 180; low._width = 80;
  const page = loadPage(tab, hubPage({ bodyChildren: [high, low], links: [high, low] }));
  assert.equal(page.error, null);
  const tip = page.doc.querySelector('.term-tip');
  tip.offsetWidth = 352;
  tip.offsetHeight = 140;

  page.doc.dispatch('mouseover', { target: high, relatedTarget: null, clientX: 210, clientY: 82 });
  assert.equal(tip.getAttribute('data-placement'), 'below');
  assert.ok(Number.parseFloat(tip.style.top) > high.getBoundingClientRect().bottom);
  assert.equal(tip.querySelector('.term-tip__escape').textContent, 'Esc to close');

  page.doc.dispatch('mouseover', { target: low, relatedTarget: null, clientX: 210, clientY: 660 });
  assert.equal(tip.getAttribute('data-placement'), 'above');
  assert.ok(
    Number.parseFloat(tip.style.top) + tip.offsetHeight < low.getBoundingClientRect().top,
    'above placement leaves a pointer-safe gap below the card',
  );
  page.doc.dispatch('keydown', { key: 'Escape' });
  assert.ok(
    tip.hidden || tip.classList.contains('is-leaving'),
    'Esc closes immediately in the shim or begins the browser fade',
  );
});

test('term preview avoids covering the remainder of its own reading block', () => {
  const tab = makeTab();
  const paragraph = makeEl('p');
  paragraph._docTop = 220; paragraph._height = 200; paragraph._left = 120; paragraph._width = 620;
  const term = makeLink('glossary.html#glossary-ai-native', 'ai-native-term');
  term.className = 'narrative-ref--term';
  term.setAttribute('data-term', 'ai-native');
  term.setAttribute('data-term-preview', 'AI-native term preview.');
  term._docTop = 225; term._height = 20; term._left = 180; term._width = 80;
  paragraph.appendChild(term);
  const page = loadPage(tab, hubPage({ bodyChildren: [paragraph], links: [term] }));
  assert.equal(page.error, null);
  const tip = page.doc.querySelector('.term-tip');
  tip.offsetWidth = 352;
  tip.offsetHeight = 140;

  page.doc.dispatch('mouseover', { target: term, relatedTarget: null, clientX: 210, clientY: 235 });
  assert.equal(tip.getAttribute('data-placement'), 'above');
  assert.ok(
    Number.parseFloat(tip.style.top) + tip.offsetHeight <= paragraph.getBoundingClientRect().top,
    'the card uses the clear side instead of covering following lines in the paragraph',
  );
});

test('term hover keeps meaning-scope policy on the glossary drilldown', () => {
  const tab = makeTab();
  const term = makeLink('glossary.html#glossary-paper', 'paper-link');
  term.className = 'narrative-ref--term';
  term.setAttribute('data-term', 'paper');

  const page = loadPage(tab, hubPage({
    bodyChildren: [term],
    links: [term],
    windowGlobals: {
      __MICROCOSM_INDEX__: {
        terms: [{
          object_id: 'term:paper',
          preferred_label: 'paper',
          reader_preview: 'A paper is a standalone scholarly or research document.',
        }],
      },
    },
  }));

  assert.equal(page.error, null);
  page.doc.dispatch('mouseover', { target: term, relatedTarget: null });
  assert.equal((term._listeners.mouseenter || []).length, 0, 'term hover stays delegated');
  assert.equal((term._listeners.focus || []).length, 0, 'term focus stays delegated');
  const tip = page.doc.querySelector('.term-tip');
  assert.ok(tip && !tip.hidden, 'hover opens the shared term preview');
  assert.equal(tip.querySelector('.term-tip__scope'), null, 'policy metadata is not repeated in the preview');
});

test('scroll dismisses only a transient pointer preview after its term leaves the pointer', () => {
  const tab = makeTab();
  const term = makeLink('glossary.html#glossary-paper', 'paper-scroll-link');
  term.className = 'narrative-ref--term';
  term.setAttribute('data-term', 'paper');
  term.setAttribute('data-term-label', 'paper');
  term.setAttribute('data-term-preview', 'A paper is a standalone research document.');
  const elsewhere = makeEl('p');
  const spec = hubPage({ bodyChildren: [term, elsewhere], links: [term] });
  spec.hitTarget = term;
  const page = loadPage(tab, spec);
  assert.equal(page.error, null);

  page.doc.dispatch('mouseover', { target: term, relatedTarget: null, clientX: 40, clientY: 40 });
  const tip = page.doc.querySelector('.term-tip');
  assert.ok(tip && !tip.hidden, 'pointer hover opens the transient preview');
  spec.hitTarget = elsewhere;
  page.fireScroll();
  assert.equal(tip.hidden, true, 'scrolling the term away dismisses its stale hover preview');

  page.doc.activeElement = term;
  page.doc.dispatch('focusin', { target: term });
  assert.equal(tip.hidden, false, 'keyboard focus opens the preview');
  spec.hitTarget = elsewhere;
  page.fireScroll();
  assert.equal(tip.hidden, false, 'scroll preserves a keyboard-focus preview');

  page.doc.dispatch('click', { target: term, button: 0, preventDefault() {} });
  assert.ok(tip.classList.contains('is-expanded'));
  page.fireScroll();
  assert.equal(tip.hidden, false, 'scroll preserves a deliberately expanded card');
});

test('term hover opens from inline preview data without loading the search index', () => {
  const tab = makeTab();
  const term = makeLink('glossary.html#glossary-ai-native', 'ai-native-link');
  term.className = 'narrative-ref--term';
  term.setAttribute('data-term', 'ai_native');
  term.setAttribute('data-term-label', 'AI-native');
  term.setAttribute(
    'data-term-preview',
    'AI-native describes a workflow designed around bounded, inspectable AI work.',
  );

  const page = loadPage(tab, hubPage({ bodyChildren: [term], links: [term] }));

  assert.equal(page.error, null);
  assert.equal(page.win.__MICROCOSM_INDEX__, undefined, 'the full search index starts absent');
  page.doc.dispatch('mouseover', { target: term, relatedTarget: null });
  const tip = page.doc.querySelector('.term-tip');
  assert.ok(tip && !tip.hidden, 'inline data opens the tooltip on the first hover');
  assert.equal(
    tip.querySelector('.term-tip__text').textContent,
    'AI-native describes a workflow designed around bounded, inspectable AI work.',
  );
  assert.equal(tip.querySelector('.term-tip__scope'), null);
  assert.equal(page.win.__MICROCOSM_INDEX__, undefined, 'hover does not pull the full index');
});

test('page JSON export redacts local filesystem origin into public site routes', async () => {
  const tab = makeTab();
  const clipboardWrites = [];
  const privateHomePrefix = '/' + ['Users', ['will', 'cook'].join('')].join('/');
  const macroRepoSegment = ['src', 'ai_workflow'].join('/');
  const article = makeEl('article');
  article.className = 'docs-article';

  const h1 = makeEl('h1');
  h1.textContent = 'Doctrine';
  article.appendChild(h1);

  const p = makeEl('p');
  const objectMap = makeLink('../object-map.json#coverage');
  objectMap.textContent = 'Object map';
  p.appendChild(objectMap);
  article.appendChild(p);

  const localAnchor = makeLink('#support');
  localAnchor.textContent = 'Support section';
  article.appendChild(localAnchor);

  const sourceLink = makeLink('https://github.com/wcook04/microcosm-substrate/blob/main/README.md');
  sourceLink.textContent = 'Source';
  article.appendChild(sourceLink);

  const exportButton = makeEl('button');
  exportButton.setAttribute('data-page-export', '');
  article.appendChild(exportButton);

  const page = loadPage(tab, {
    path: `${privateHomePrefix}/${macroRepoSegment}/sites/microcosm/docs/doctrine.html`,
    search: '?local=1',
    hash: '#overview',
    title: 'Doctrine · Microcosm',
    bodyChildren: [article],
    clipboard: {
      writeText(text) {
        clipboardWrites.push(String(text));
        return Promise.resolve();
      },
    },
  });

  assert.equal(page.error, null);
  exportButton.dispatch('click', {});
  await new Promise((resolve) => setImmediate(resolve));
  assert.equal(clipboardWrites.length, 1, 'export copies the JSON payload');
  const payload = JSON.parse(clipboardWrites[0]);
  const serialized = JSON.stringify(payload);

  assert.equal(payload.source.url, 'docs/doctrine.html?local=1#overview');
  assert.equal(payload.source.path, 'docs/doctrine.html');
  assert.ok(payload.links.some((row) => row.href === 'object-map.json#coverage'));
  assert.ok(payload.links.some((row) => row.href === 'docs/doctrine.html?local=1#support'));
  assert.ok(payload.links.some((row) => row.href === 'https://github.com/wcook04/microcosm-substrate/blob/main/README.md'));
  assert.equal(serialized.includes(privateHomePrefix), false, 'local home path must not leak');
  assert.equal(serialized.includes('file://'), false, 'file URL origin must not leak');
  assert.equal(serialized.includes(macroRepoSegment), false, 'macro repo path must not leak');
});

test('already-open details deep links align the visible summary over post-expansion frames', () => {
  const tab = makeTab();
  const previous = makeDetails('paper-module-early');
  previous.open = true;
  previous._docTop = 100;
  previous._height = 3200;

  const target = makeDetails('paper-module-late');
  target.open = true; // mirrors native/browser-opened details before the JS correction runs
  target._docTop = 899;
  target._height = 4200;
  const summary = makeEl('summary');
  summary._docTop = 900;
  summary._height = 32;
  target.appendChild(summary);

  const page = loadPage(tab, paperModulesPage({
    hash: '#paper-module-late',
    openDetails: [previous, target],
    byId: [previous, target],
  }));

  assert.equal(page.error, null);
  assert.equal(target.open, true, 'the target card remains open');
  assert.equal(tab.scrollToCalls.length, 3, 'post-expansion correction runs across multiple frames');
  assert.deepEqual(tab.scrollToCalls, [900, 900, 900], 'the summary, not the tall details box, is the stable anchor');
  assert.equal(tab.lastScrollTo, 900, 'final correction leaves the summary at the top of the viewport');
});

test('preview helper scrolls to a numbered diagram and opens its paper-module card', () => {
  const tab = makeTab();
  const target = makeDetails('paper-module-late');
  target.open = false;
  target._docTop = 700;
  const summary = makeEl('summary');
  summary._docTop = 700;
  summary._height = 32;
  target.appendChild(summary);

  const diagram = makeEl('figure');
  diagram.id = 'paper-module-late-diagram-1';
  diagram.className = 'pm-diagram reader-stage__item';
  diagram.setAttribute('data-reader-stage', 'diagram');
  diagram._docTop = 1180;
  diagram._height = 300;
  target.appendChild(diagram);

  const page = loadPage(tab, paperModulesPage({
    openDetails: [target],
    byId: [target, diagram],
    diagrams: [diagram],
  }));

  assert.equal(page.error, null);
  assert.equal(typeof page.preview().scrollToDiagram, 'function', 'agent preview helper is exposed');
  const receipt = page.preview().scrollToDiagram(1);
  assert.equal(target.open, true, 'scrolling a diagram opens its ancestor card first');
  assert.equal(receipt.ok, true);
  assert.equal(receipt.id, 'paper-module-late-diagram-1');
  assert.equal(receipt.hash, '#paper-module-late-diagram-1');
  assert.equal(receipt.scroller, 'document');
  assert.equal(tab.lastScrollTo, 1180, 'diagram, not page top, is the final aligned target');
});

test('landing -> docs hop offers the return pill with the landing title', () => {
  const tab = makeTab();
  const landing = loadPage(tab, landingPage({ scrollY: 700 }));
  landing.firePagehide(); // leaving the landing pushes it onto the trail
  const hub = loadPage(tab, hubPage());
  assert.equal(hub.error, null);
  assert.equal(hub.pillCount(), 1, 'exactly one pill on arrival');
  assert.equal(hub.pillWhere(), 'Microcosm', 'colon-title trims to a short label');
  assert.equal(hub.pillAria(), 'Back to previous view: Microcosm');
  assert.equal(hub.stack().length, 1, 'trail holds the landing view');
});

test('clicking the pill restores landing scroll + keyboard focus and empties the trail', () => {
  const tab = makeTab();
  const landing = loadPage(tab, landingPage({ scrollY: 700 }));
  landing.firePagehide();
  const hub = loadPage(tab, hubPage());

  const href = hub.clickPill();
  assert.equal(href, '/', 'pill navigates to the landing url');
  assert.equal(hub.stack().length, 0, 'the hop just taken is popped from the trail');
  assert.equal(hub.restore().path, '/', 'a pending exact-restore is staged for the landing');
  hub.firePagehide(); // the return hop must NOT re-push the page we are leaving
  assert.equal(hub.stack().length, 0, 'suppress flag keeps the return hop from re-stacking');

  // The browser now loads the landing again; the pending restore applies.
  const back = loadPage(tab, landingPage()); // navType navigate (scripted href assignment)
  assert.equal(back.error, null);
  assert.equal(tab.lastScrollTo, 700, 'exact scroll position is restored');
  const link = back.page.links[0];
  assert.equal(link._focused, true, 'keyboard focus returns to the invoking control');
  assert.equal(link._focusPreventScroll, true, 'focus uses preventScroll so it cannot fight the scroll restore');
  assert.equal(back.restore(), null, 'the pending restore is consumed exactly once');
  assert.equal(back.pillCount(), 0, 'trail exhausted -> no pill');
});

test('multi-hop unwind: hub -> architecture(y=600) -> area, then back restores architecture scroll', () => {
  const tab = makeTab();
  loadPage(tab, hubPage()).firePagehide();                 // push hub
  const arch = loadPage(tab, archPage({ scrollY: 600 }));
  assert.equal(arch.pillWhere(), 'Overview');
  arch.firePagehide();                                     // push architecture (y=600)
  const area = loadPage(tab, areaPage());
  assert.equal(area.pillWhere(), 'How it fits together');
  assert.equal(area.stack().length, 2, 'trail = [hub, architecture]');

  const href = area.clickPill();
  assert.equal(href, '/docs/architecture.html');
  area.firePagehide();
  const back = loadPage(tab, archPage(partsOf('/docs/architecture.html')));
  assert.equal(tab.lastScrollTo, 600, 'architecture scroll restored');
  assert.equal(back.pillWhere(), 'Overview', 'pill now points one hop further back, to the hub');
  assert.equal(back.stack().length, 1, 'trail = [hub]');
});

test('open-card state is captured and restored on return', () => {
  const tab = makeTab();
  loadPage(tab, hubPage()).firePagehide();
  const openCard = makeDetails('component-finance');
  openCard.open = true;
  const arch = loadPage(tab, archPage({ openDetails: [openCard] }));
  arch.firePagehide(); // snapshot captures open=['component-finance']
  const area = loadPage(tab, areaPage());
  assert.deepEqual(area.stack()[area.stack().length - 1].open, ['component-finance']);

  area.clickPill();
  area.firePagehide();
  const closedCard = makeDetails('component-finance'); // arrives shut (native fragment nav does not open it)
  closedCard.open = false;
  loadPage(tab, archPage({ openDetails: [closedCard], byId: [closedCard] }));
  assert.equal(closedCard.open, true, 'the card the reader had open is reopened on return');
});

test('golden reader route unwinds map hash, component disclosure, and full-module jump', () => {
  const componentId = 'component-cold_reader_route_map';
  const moduleId = 'paper-module-cold-reader-route-map';
  const mapHash = '#map=component%3Acold_reader_route_map';
  const componentHash = `#${componentId}`;
  const moduleHash = `#${moduleId}`;
  const readFullHref = `paper-modules.html#${moduleId}`;
  const readFullId = 'read-full-cold-reader-route-map';

  const tab = makeTab();
  loadPage(tab, landingPage({ scrollY: 710 })).firePagehide();
  const hub = loadPage(tab, hubPage({ scrollY: 120 }));
  assert.equal(hub.pillWhere(), 'Microcosm');
  hub.firePagehide();

  const arch = loadPage(tab, archPage({ hash: mapHash, scrollY: 640 }));
  assert.equal(arch.pillWhere(), 'Overview');
  arch.firePagehide();

  const openCard = makeDetails(componentId);
  openCard.open = true;
  const readFull = makeLink(readFullHref, readFullId);
  const component = loadPage(tab, componentPage({
    hash: componentHash,
    scrollY: 880,
    openDetails: [openCard],
    byId: [openCard, readFull],
    active: readFull,
  }));
  assert.equal(component.pillWhere(), 'How it fits together');
  component.firePagehide();

  const module = loadPage(tab, paperModulesPage({ hash: moduleHash }));
  assert.equal(module.pillWhere(), 'Components');
  assert.equal(module.stack().length, 4, 'trail = [landing, overview, map hash, component card]');

  const componentHref = module.clickPill();
  assert.equal(componentHref, `/docs/components.html${componentHash}`);
  module.firePagehide();

  tab.lastScrollTo = undefined;
  const closedCard = makeDetails(componentId);
  const readFullAgain = makeLink(readFullHref, readFullId);
  const componentBack = loadPage(tab, componentPage({
    hash: componentHash,
    openDetails: [closedCard],
    byId: [closedCard, readFullAgain],
  }));
  assert.equal(closedCard.open, true, 'local disclosure reopens when returning from the full module');
  assert.equal(readFullAgain._focused, true, 'focus returns to the Read full module control');
  assert.equal(readFullAgain._focusPreventScroll, true, 'focus restore cannot fight scroll restore');
  assert.equal(tab.lastScrollTo, 880, 'component scroll is restored');
  assert.equal(componentBack.pillWhere(), 'How it fits together');

  const archHref = componentBack.clickPill();
  assert.equal(archHref, `/docs/architecture.html${mapHash}`);
  componentBack.firePagehide();

  tab.lastScrollTo = undefined;
  const archBack = loadPage(tab, archPage({ hash: mapHash }));
  assert.equal(archBack.loc.hash, mapHash, 'map selection hash survives the exact return');
  assert.equal(tab.lastScrollTo, 640, 'map scroll is restored');
  assert.equal(archBack.pillWhere(), 'Overview');

  const overviewHref = archBack.clickPill();
  assert.equal(overviewHref, '/docs/index.html');
  archBack.firePagehide();

  tab.lastScrollTo = undefined;
  const hubBack = loadPage(tab, hubPage());
  assert.equal(tab.lastScrollTo, 120, 'overview scroll is restored');
  assert.equal(hubBack.pillWhere(), 'Microcosm');

  const landingHref = hubBack.clickPill();
  assert.equal(landingHref, '/');
  hubBack.firePagehide();

  tab.lastScrollTo = undefined;
  const landingBack = loadPage(tab, landingPage());
  assert.equal(tab.lastScrollTo, 710, 'landing scroll is restored at the end of the route');
  assert.equal(landingBack.pillCount(), 0, 'the golden reader route exhausts cleanly back at the start');
});

test('direction-aware reconcile: a FORWARD click to a previously-visited page KEEPS the trail', () => {
  const tab = makeTab();
  loadPage(tab, hubPage()).firePagehide();        // [hub]
  loadPage(tab, archPage()).firePagehide();       // [hub, architecture]
  const area = loadPage(tab, areaPage());
  area.firePagehide();                            // [hub, architecture, area]
  // Forward navigation (a normal click) back to architecture, already in the trail:
  const reland = loadPage(tab, archPage({ navType: 'navigate' }));
  assert.equal(reland.stack().length, 3, 'a forward click must NOT truncate an earlier occurrence');
  assert.equal(reland.pillWhere(), 'Architecture & navigation', 'pill points to the page just left (area)');
});

test('Back/Forward traversal reconciles by truncating from the landed page forward', () => {
  const tab = makeTab();
  loadPage(tab, hubPage()).firePagehide();        // [hub]
  loadPage(tab, archPage()).firePagehide();       // [hub, architecture]
  const area = loadPage(tab, areaPage());
  area.firePagehide();                            // [hub, architecture, area]
  // Browser Back to architecture:
  const back = loadPage(tab, archPage({ navType: 'back_forward' }));
  assert.equal(back.stack().length, 1, 'trail truncates to everything behind the landed page');
  assert.equal(back.pillWhere(), 'Overview', 'pill points to the hub');
});

test('reload strips only the self-push, preserving the deeper trail', () => {
  const tab = makeTab();
  loadPage(tab, hubPage()).firePagehide();        // [hub]
  const arch = loadPage(tab, archPage());         // on architecture, trail [hub]
  arch.firePagehide();                            // [hub, architecture]
  const reloaded = loadPage(tab, archPage({ navType: 'reload' }));
  assert.equal(reloaded.stack().length, 1, 'the self-push from the reload is stripped');
  assert.equal(reloaded.stack()[0].path, '/docs/index.html', 'the hub stays in the trail');
  assert.equal(reloaded.pillWhere(), 'Overview');
});

test('BFCache pageshow recomputes the pill idempotently against the live trail', () => {
  const tab = makeTab();
  loadPage(tab, hubPage()).firePagehide();        // [hub]
  const arch = loadPage(tab, archPage());         // pill: "Back to Overview"
  assert.equal(arch.pillWhere(), 'Overview');
  assert.equal(arch.pillCount(), 1);

  // The trail advances underneath this frozen page (a deeper view recorded
  // elsewhere in the tab), then the page is restored from the back/forward cache.
  tab.store.setItem('mc:viewstate:stack', JSON.stringify([
    { url: '/docs/index.html', path: '/docs/index.html', title: 'Overview', y: 0, open: [], focus: null },
    { url: '/docs/evidence.html', path: '/docs/evidence.html', title: 'Evidence', y: 0, open: [], focus: null },
  ]));
  arch.firePageshow(true);
  assert.equal(arch.pillCount(), 1, 'no duplicate pill after a BFCache restore');
  assert.equal(arch.pillWhere(), 'Evidence', 'pill label tracks the advanced trail');
});

test('sessionStorage unavailable: feature switches off, no crash, no pill', () => {
  const tab = makeTab({ blockedStorage: true });
  const landing = loadPage(tab, landingPage({ scrollY: 300 }));
  assert.equal(landing.error, null, 'a blocked store must not crash the page');
  assert.equal(landing.pillCount(), 0, 'no affordance when storage is off');
  // Leaving must not throw either (pagehide handler probes storage defensively).
  assert.doesNotThrow(() => landing.firePagehide());
  const hub = loadPage(tab, hubPage());
  assert.equal(hub.error, null);
  assert.equal(hub.pillCount(), 0, 'still no trail without storage');
});

test('no self-referential pill: a trail head equal to the current page shows nothing', () => {
  const tab = makeTab();
  // Seed a trail whose head is the page we are about to render.
  tab.store.setItem('mc:viewstate:stack', JSON.stringify([
    { url: '/docs/index.html', path: '/docs/index.html', title: 'Overview', y: 0, open: [], focus: null },
  ]));
  // Arrive on the hub via a forward navigation; reconcile strips the self-head.
  const hub = loadPage(tab, hubPage({ navType: 'navigate' }));
  assert.equal(hub.pillCount(), 0, 'reconcile drops a same-path head so the pill never points at "here"');
});

// Collect every prefers-reduced-motion block by matching braces, rather than
// stopping at the first `}}`. The stylesheet carries several such blocks —
// narrow ones for the theme toggle, the pill's own opacity, the author email —
// alongside the universal guard, and their order is not a contract.
function reducedMotionBlocks(css) {
  const blocks = [];
  const opener = /@media\s*\(prefers-reduced-motion:\s*reduce\)\s*\{/g;
  let match;
  while ((match = opener.exec(css)) !== null) {
    let depth = 1;
    let i = match.index + match[0].length;
    while (i < css.length && depth > 0) {
      if (css[i] === '{') depth += 1;
      else if (css[i] === '}') depth -= 1;
      i += 1;
    }
    blocks.push(css.slice(match.index, i));
  }
  return blocks;
}

test('reduced-motion CSS guard: the global transition override covers the viewback pill', () => {
  const css = readFileSync(STYLE_CSS, 'utf8');
  const blocks = reducedMotionBlocks(css);
  assert.ok(blocks.length > 0, 'a prefers-reduced-motion block must exist');
  // What matters is that *some* block carries the universal override, since that
  // is what reaches .viewback. Asserting against whichever block happens to come
  // first made this fail the moment a narrower rule was added above it, while
  // the guard it was checking for was still present and still working.
  const universal = blocks.filter((block) => /\*,\s*\*::before,\s*\*::after/.test(block));
  assert.equal(
    universal.length, 1,
    `exactly one prefers-reduced-motion block should carry the universal override; found ${universal.length} of ${blocks.length}`,
  );
  assert.match(universal[0], /transition-duration:\s*0\.01ms\s*!important/, 'transitions collapse so the pill does not animate');
  assert.match(universal[0], /animation-duration:\s*0\.01ms\s*!important/, 'animations collapse too, so nothing re-enters by keyframe');
});
