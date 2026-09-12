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
    get firstChild() { return this.children[0] || null; },
    get nextSibling() {
      if (!this.parentNode) return null;
      return this.parentNode.children[this.parentNode.children.indexOf(this) + 1] || null;
    },
    get nodeValue() { return this.nodeType === 3 ? this._text : null; },
    parentNode: null,
    parentElement: null,
    className: '',
    style: {},
    type: '',
    value: '',
    open: false,
    hidden: false,
    _html: '',
    get innerHTML() { return this._html; },
    set innerHTML(value) {
      this._html = String(value);
      this._text = this._html.replace(/<[^>]*>/g, '').replace(/&quot;/g, '"').replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&amp;/g, '&');
      this.children = [];
    },
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
    hasAttribute(k) { return Object.prototype.hasOwnProperty.call(this._attrs, k); },
    removeAttribute(k) { delete this._attrs[k]; if (k === 'hidden') this.hidden = false; },
    appendChild(c) { c.parentNode = this; c.parentElement = this.nodeType === 1 ? this : null; this.children.push(c); return c; },
    insertBefore(c, before) {
      if (c.parentNode) c.parentNode.removeChild(c);
      const index = this.children.indexOf(before);
      c.parentNode = this;
      c.parentElement = this.nodeType === 1 ? this : null;
      if (index < 0) this.children.push(c); else this.children.splice(index, 0, c);
      return c;
    },
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
    getClientRects() {
      let node = this;
      while (node) { if (node.hidden) return []; node = node.parentNode; }
      return [this.getBoundingClientRect()];
    },
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
    const prefix = attr[1].endsWith('^');
    const actual = attrValue(node, prefix ? attr[1].slice(0, -1) : attr[1]);
    if (actual == null) return false;
    if (attr[2] != null && (prefix ? !actual.startsWith(attr[2]) : actual !== attr[2])) return false;
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
      if (!event.stopImmediatePropagation) {
        event.stopImmediatePropagation = () => { event._immediateStopped = true; };
      }
      for (const fn of (docListeners[type] || []).slice()) {
        fn(event);
        if (event._immediateStopped) break;
      }
    },
    dispatchEvent(event) { this.dispatch(event.type, event); return true; },
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
    URLSearchParams,
    history: {
      state: null,
      pushState() {},
      replaceState(state, _unused, url) {
        this.state = state;
        const parsed = new URL(url, loc.href);
        loc.pathname = parsed.pathname;
        loc.search = parsed.search;
        loc.hash = parsed.hash;
      },
    },
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
    requestAnimationFrame: win.requestAnimationFrame,
    cancelAnimationFrame() {},
    navigator: { clipboard: page.clipboard === undefined ? null : page.clipboard, userAgent: 'node-harness' },
    console: { log() {}, warn() {}, error() {}, info() {}, debug() {} },
    setTimeout(fn) { try { fn(); } catch (e) {} return 0; },
    clearTimeout() {},
    URL,
    URLSearchParams,
    CustomEvent: class CustomEvent { constructor(type, init = {}) { this.type = type; this.detail = init.detail; } },
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
    fireHashchange() {
      let stopped = false;
      const event = { stopImmediatePropagation() { stopped = true; } };
      for (const fn of (winListeners.hashchange || [])) { fn(event); if (stopped) break; }
    },
    firePopstate(state = win.history.state) { (winListeners.popstate || []).forEach((fn) => fn({ state })); },
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
  assert.doesNotMatch(SOURCE, /warmTermLayer/);
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
  assert.match(SOURCE, /links\.length > 80\) return/);
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
  assert.equal(tip.querySelector('.term-tip__text').textContent,
    'A system is a set of connected parts. System card: connected parts with a shared boundary.');
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
  assert.equal(tip.querySelector('.term-tip__text').textContent,
    'A system is a set of connected parts. System card: connected parts with a shared boundary.');
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

test('notation help bootstraps without prose anchors and stays lazy until intent', () => {
  const tab = makeTab();
  const math = makeEl('span');
  math.className = 'math inline';
  math.setAttribute('data-tex', String.raw`\(\forall x\in A\)`);
  const mathml = makeEl('math');
  mathml.appendChild(makeEl('mi'));
  math.appendChild(mathml);
  const originalTex = math.getAttribute('data-tex');
  const originalChild = math.children[0];
  const page = loadPage(tab, hubPage({ bodyChildren: [math] }));

  assert.equal(page.error, null);
  assert.equal(typeof page.win.PlectisTermHelp.registerNotation, 'function');
  assert.equal(page.doc.head.querySelector('script[data-term-previews]'), null,
    'a docs page with no prose terms does not fetch glossary data at idle');
  page.win.PlectisTermHelp.registerNotation(math, ['universal_quantifier', 'set_membership']);
  assert.equal(math.getAttribute('tabindex'), '0');
  assert.equal(math.getAttribute('data-tex'), originalTex);
  assert.equal(math.children[0], originalChild, 'registration preserves the rendered MathML subtree');

  page.doc.activeElement = math;
  page.doc.dispatch('focusin', { target: math });
  assert.ok(page.doc.head.querySelector('script[data-term-previews]'),
    'the first real notation intent starts the existing lazy payload');
});

test('notation registration controls sequential focus without overriding existing tab stops', () => {
  const defaults = makeEl('span');
  const explicit = makeEl('span');
  const pointerOnly = makeEl('span');
  const wideEquation = makeEl('span');
  wideEquation.setAttribute('tabindex', '0');
  const programmatic = makeEl('span');
  programmatic.setAttribute('tabindex', '-1');
  const page = loadPage(makeTab(), hubPage({
    bodyChildren: [defaults, explicit, pointerOnly, wideEquation, programmatic],
  }));
  assert.equal(page.error, null);
  const register = page.win.PlectisTermHelp.registerNotation;
  register(defaults, ['sum']);
  register(explicit, ['sum'], { keyboardFocus: true });
  register(pointerOnly, ['sum'], { keyboardFocus: false });
  register(wideEquation, ['sum'], { keyboardFocus: false });
  register(programmatic, ['sum'], { keyboardFocus: true });

  assert.equal(defaults.getAttribute('tabindex'), '0', 'default help remains keyboard reachable');
  assert.equal(explicit.getAttribute('tabindex'), '0');
  assert.equal(pointerOnly.getAttribute('tabindex'), '-1', 'repeated notation stays programmatically focusable');
  assert.equal(wideEquation.getAttribute('tabindex'), '0', 'scrollable equations keep their existing tab stop');
  assert.equal(programmatic.getAttribute('tabindex'), '-1', 'an existing focus policy remains authoritative');
});

test('notation focus cycles records, escapes, reopens, and keeps popup focus local', () => {
  const tab = makeTab();
  const math = makeEl('span');
  math.className = 'math inline';
  math.setAttribute('data-tex', String.raw`\(\sum_i a_i \prod_j b_j\)`);
  const page = loadPage(tab, hubPage({
    bodyChildren: [math],
    windowGlobals: { __MICROCOSM_TERM_PREVIEWS__: { terms: [
      { object_id: 'term:sum', preferred_label: 'Sum', reader_preview: 'Adds indexed terms.' },
      { object_id: 'term:product', preferred_label: 'Product', reader_preview: 'Multiplies indexed terms.' },
    ] } },
  }));
  assert.equal(page.error, null);
  page.win.PlectisTermHelp.registerNotation(math, ['sum', 'product']);
  page.doc.activeElement = math;
  page.doc.dispatch('focusin', { target: math });
  const tip = page.doc.querySelector('.term-tip');
  assert.equal(tip.querySelector('.term-tip__label').textContent, 'Sum');
  assert.equal(tip.querySelector('.term-tip__back').textContent, 'Back to page');
  assert.ok(queryAll(tip, '.term-tip__back').some((el) => el.textContent === 'Previous notation'));
  assert.ok(queryAll(tip, '.term-tip__back').some((el) => el.textContent === 'Next notation'));

  page.doc.dispatch('keydown', { key: 'ArrowRight', target: math, preventDefault() {} });
  assert.equal(tip.querySelector('.term-tip__label').textContent, 'Product');
  const elsewhere = makeEl('button');
  page.doc.activeElement = elsewhere;
  page.doc.dispatch('keydown', { key: 'ArrowLeft', target: elsewhere, preventDefault() { throw new Error('global arrow hijack'); } });
  assert.equal(tip.querySelector('.term-tip__label').textContent, 'Product', 'arrows elsewhere do not cycle notation');

  page.doc.dispatch('keydown', { key: 'Escape', target: elsewhere });
  assert.equal(tip.hidden, true);
  page.doc.activeElement = math;
  page.doc.dispatch('keydown', { key: 'Enter', target: math, preventDefault() {} });
  assert.equal(tip.hidden, false, 'Enter reopens after Escape without requiring a new focus event');
  assert.ok(tip.classList.contains('is-expanded'));

  const previous = queryAll(tip, '.term-tip__back').find((el) => el.textContent === 'Previous notation');
  page.doc.activeElement = previous;
  tip.dispatch('focusin', { target: previous, relatedTarget: math });
  const next = queryAll(tip, '.term-tip__back').find((el) => el.textContent === 'Next notation');
  tip.dispatch('focusout', { target: previous, relatedTarget: next });
  assert.equal(tip.hidden, false, 'moving between popup controls retains the popup');
  page.doc.activeElement = previous;
  page.doc.dispatch('keydown', { key: 'Escape', target: previous, preventDefault() {} });
  assert.equal(tip.hidden, true, 'Escape from a popup control dismisses the card');
  assert.equal(math._focused, true, 'Escape from a popup control restores expression focus');
});

test('cold notation Enter initializes once and cannot become same-event navigation', () => {
  const tab = makeTab();
  const math = makeEl('span');
  const page = loadPage(tab, hubPage({ bodyChildren: [math] }));
  assert.equal(page.error, null);
  page.win.PlectisTermHelp.registerNotation(math, ['sum'], {
    hrefForId: () => 'glossary.html#glossary-sum',
  });
  page.win.__MICROCOSM_TERM_PREVIEWS__ = { terms: [
    { object_id: 'term:sum', preferred_label: 'Sum', reader_preview: 'Adds indexed terms.' },
  ] };
  page.doc.activeElement = math;
  let stopped = false;
  page.doc.dispatch('keydown', {
    key: 'Enter', target: math,
    preventDefault() {},
    stopImmediatePropagation() { stopped = true; this._immediateStopped = true; },
  });
  const tip = page.doc.querySelector('.term-tip');
  assert.equal(stopped, true, 'the consumed cold event cannot reach newly installed listeners');
  assert.ok(tip && !tip.hidden && tip.classList.contains('is-expanded'));
  assert.equal(tab.pendingHref, null, 'first Enter stays on-page even when records were synchronously available');
});

test('delayed missing-only notation clicks never resolve a URL with an absent ID', () => {
  const tab = makeTab();
  const math = makeEl('span');
  const page = loadPage(tab, hubPage({ bodyChildren: [math] }));
  assert.equal(page.error, null);
  let hrefCalls = 0;
  page.win.PlectisTermHelp.registerNotation(math, ['missing'], {
    hrefForId(id) {
      hrefCalls += 1;
      return 'glossary.html#glossary-' + id.replace(/_/g, '-');
    },
  });
  let prevented = false;
  page.doc.dispatch('click', {
    target: math, button: 0,
    preventDefault() { prevented = true; },
  });
  assert.equal(prevented, true);
  const script = page.doc.head.querySelector('script[data-term-previews]');
  assert.ok(script, 'a cold click starts the delayed glossary request');
  page.win.__MICROCOSM_TERM_PREVIEWS__ = { terms: [
    { object_id: 'term:sum', reader_preview: 'Adds indexed terms.' },
  ] };

  assert.doesNotThrow(() => script.dispatch('load'), 'missing records cannot reach the URL callback');
  assert.equal(hrefCalls, 0);
  assert.equal(tab.pendingHref, null, 'missing notation does not navigate to an invalid fragment');
  const tip = page.doc.querySelector('.term-tip');
  assert.ok(!tip || tip.hidden, 'missing records do not leave an empty popup visible');
});

test('notation culls missing IDs once, clears stale cards, and keeps prose behavior', () => {
  const tab = makeTab();
  let objectIdReads = 0;
  const sum = { preferred_label: 'Sum', reader_preview: 'Adds indexed terms.' };
  Object.defineProperty(sum, 'object_id', { get() { objectIdReads += 1; return 'term:sum'; } });
  const prose = makeLink('glossary.html#glossary-system', 'system');
  prose.className = 'narrative-ref--term';
  prose.setAttribute('data-term', 'system');
  prose.setAttribute('data-term-preview', 'Connected parts.');
  const valid = makeEl('span');
  const missing = makeEl('span');
  const page = loadPage(tab, hubPage({
    bodyChildren: [prose, valid, missing], links: [prose],
    windowGlobals: { __MICROCOSM_TERM_PREVIEWS__: { terms: [sum,
      { object_id: 'term:system', preferred_label: 'System', reader_preview: 'Connected parts.' },
    ] } },
  }));
  assert.equal(page.error, null);
  page.win.PlectisTermHelp.registerNotation(valid, ['missing', 'sum', 'sum']);
  page.win.PlectisTermHelp.registerNotation(missing, ['absent']);
  page.doc.activeElement = valid;
  page.doc.dispatch('focusin', { target: valid });
  const tip = page.doc.querySelector('.term-tip');
  assert.equal(tip.querySelector('.term-tip__label').textContent, 'Sum');
  const readsAfterFirstResolution = objectIdReads;
  page.doc.dispatch('focusin', { target: valid });
  page.doc.dispatch('mouseover', { target: valid, relatedTarget: null });
  assert.equal(objectIdReads, readsAfterFirstResolution, 'repeat intent does not rebuild or re-read glossary records');
  page.doc.activeElement = missing;
  page.doc.dispatch('focusin', { target: missing });
  assert.equal(tip.hidden, true, 'a trigger with no valid records clears the previous card');

  let prevented = false;
  page.doc.dispatch('click', { target: prose, button: 0, preventDefault() { prevented = true; } });
  assert.equal(prevented, true);
  assert.ok(tip.classList.contains('is-expanded'), 'the existing prose first-click expansion remains active');
});

for (const action of ['text', '']) {
  test(`page ${action || 'JSON'} export preserves TeX behind rendered glyphs`, async () => {
    const writes = [];
    const article = makeEl('article');
    article.className = 'docs-article';
    const heading = makeEl('h1');
    heading.textContent = 'A maths paper';
    article.appendChild(heading);
    const expressions = [String.raw`\(\frac{1}{n} < 1\)`, String.raw`\[\sum_{n=1}^{\infty} a_n\]`];
    const spans = expressions.map((tex, index) => {
      const span = makeEl('span');
      span.className = `math ${index ? 'display' : 'inline'}`;
      span.setAttribute('data-tex', tex);
      span.textContent = 'typeset glyph placeholder';
      article.appendChild(span);
      return span;
    });
    const identifierName = 'irrational_erdosSupportSeries_of_summable_reciprocal';
    const identifierButton = makeEl('button');
    identifierButton.className = 'lean-identifier';
    const identifierCode = makeEl('code'); identifierCode.textContent = identifierName;
    identifierButton.appendChild(identifierCode); article.appendChild(identifierButton);
    const hidden = makeEl('span');
    hidden.className = 'math inline';
    hidden.setAttribute('data-tex', 'hidden formula');
    hidden.setAttribute('hidden', '');
    article.appendChild(hidden);
    const button = makeEl('button');
    button.setAttribute('data-page-export', action);
    article.appendChild(button);
    const page = loadPage(makeTab(), {
      path: '/plectis/maths/papers/sample.html', bodyChildren: [article],
      clipboard: { writeText(value) { writes.push(String(value)); return Promise.resolve(); } },
    });
    assert.equal(page.error, null);
    button.dispatch('click', {});
    await new Promise((resolve) => setImmediate(resolve));
    assert.equal(writes.length, 1);
    const text = action === 'text' ? writes[0] : JSON.parse(writes[0]).source_text;
    for (const tex of expressions) assert.ok(text.includes(tex), tex);
    assert.ok(text.includes(identifierName), 'disclosure controls retain their full Lean source names');
    assert.equal(text.includes('typeset glyph placeholder'), false);
    assert.equal(text.includes('hidden formula'), false);
    assert.ok(spans.every((span) => span.textContent === 'typeset glyph placeholder'));
  });
}

for (const action of ['text', '']) {
  test(`page ${action || 'JSON'} export includes unopened definitions without changing live cards`, async () => {
    const writes = [];
    const article = makeEl('article'); article.className = 'docs-article';
    const card = makeDetails('glossary-sample');
    const shell = makeEl('noscript'); shell.setAttribute('data-term-body', '');
    shell.textContent = '<p>A core <strong>definition</strong> and its fuller explanation.</p>';
    card.appendChild(shell); article.appendChild(card);
    const button = makeEl('button'); button.setAttribute('data-page-export', action);
    article.appendChild(button);
    const page = loadPage(makeTab(), {
      path: '/docs/glossary.html', bodyChildren: [article],
      clipboard: { writeText(text) { writes.push(text); return Promise.resolve(); } },
    });
    assert.equal(page.error, null);
    const create = page.doc.createElement.bind(page.doc);
    page.doc.createElement = (tag) => {
      const element = create(tag);
      if (tag === 'template') {
        // The harness's existing HTML decoder supplies this text-only fixture's
        // parsed template content. Actual nested markup is covered in-browser.
        Object.defineProperty(element, 'content', { get() {
          const text = makeEl('#text'); text.textContent = element.textContent;
          return text;
        } });
      }
      return element;
    };
    const expected = 'A core definition and its fuller explanation.';
    for (const opened of [false, true]) {
      if (opened) {
        card.removeChild(shell);
        const paragraph = makeEl('p');
        const text = makeEl('#text'); text.textContent = expected;
        paragraph.appendChild(text);
        card.appendChild(paragraph); card.open = true;
      }
      button.dispatch('click', {});
      await new Promise((resolve) => setImmediate(resolve));
      const text = action === 'text' ? writes.at(-1) : JSON.parse(writes.at(-1)).source_text;
      assert.ok(text.includes(expected), 'deferred and hydrated definitions export identically');
      assert.equal(/<\/?(?:p|strong)\b/.test(text), false, 'readable text contains no serialized markup');
      assert.equal(card.open, opened, 'export does not expand the live card');
      assert.equal(card.querySelector('noscript[data-term-body]') === shell, !opened);
    }
  });
}

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

test('cold browser Back restores the exact filtered card before truncating its snapshot', () => {
  const tab = makeTab();
  loadPage(tab, hubPage()).firePagehide();
  const card = makeDetails('component-cold_reader_route_map');
  card.open = true;
  const link = makeLink('component-cold-reader-route-map.html', 'open-component');
  loadPage(tab, componentPage({
    search: '?filter=Cold+Reader', scrollY: 1166,
    openDetails: [card], byId: [card, link], active: link,
  })).firePagehide();
  loadPage(tab, areaPage()).firePagehide();

  const restoredCard = makeDetails(card.id);
  const restoredLink = makeLink('component-cold-reader-route-map.html', link.id);
  const back = loadPage(tab, componentPage({
    search: '?filter=Cold+Reader', navType: 'back_forward',
    openDetails: [restoredCard], byId: [restoredCard, restoredLink],
  }));
  assert.equal(back.error, null);
  assert.equal(restoredCard.open, true, 'a fresh history document reopens the card');
  assert.equal(restoredLink._focused, true, 'focus returns to the invoking component link');
  assert.equal(tab.lastScrollTo, 1166, 'reading position is restored after the card opens');
  assert.equal(back.loc.search, '?filter=Cold+Reader');
  assert.equal(back.restore(), null, 'the rescued snapshot is consumed exactly once');
  assert.deepEqual(back.stack().map(entry => entry.path), ['/docs/index.html']);

  back.firePagehide();
  tab.lastScrollTo = undefined;
  const reloadCard = makeDetails(card.id);
  loadPage(tab, componentPage({
    search: '?filter=Cold+Reader', navType: 'reload', openDetails: [reloadCard],
  }));
  assert.equal(reloadCard.open, false, 'the history restore cannot leak into a later reload');
  assert.equal(tab.lastScrollTo, undefined);
});

test('cold history scroll recovery wins over queued initial fragment alignment', () => {
  const tab = makeTab();
  const id = 'component-cold_reader_route_map';
  const hash = `#${id}`;
  const url = `/docs/components.html?filter=Cold+Reader${hash}`;
  tab.store.setItem('mc:viewstate:stack', JSON.stringify([
    { path: '/docs/components.html', url, title: 'Components', y: 1037.5, open: [id], focus: null },
    { path: '/docs/area-architecture.html', url: '/docs/area-architecture.html', title: 'Area', y: 0, open: [], focus: null },
  ]));
  const card = makeDetails(id);
  card._docTop = 588;
  card.scrollIntoView = () => { tab.lastScrollTo = 588; };
  const summary = makeEl('summary');
  summary._docTop = 588;
  summary._height = 32;
  card.appendChild(summary);
  const frames = [];
  const page = loadPage(tab, componentPage({
    search: '?filter=Cold+Reader', hash, navType: 'back_forward',
    openDetails: [card], byId: [card],
    windowGlobals: { requestAnimationFrame(fn) { frames.push(fn); return frames.length; } },
  }));
  assert.equal(page.error, null);
  for (let count = 0; frames.length && count < 20; count += 1) frames.shift()();
  assert.equal(frames.length, 0);
  assert.equal(card.open, true);
  assert.equal(tab.lastScrollTo, 1037.5, 'later fragment frames cannot jump back to the summary');
  assert.equal(page.restore(), null);
});

test('cold history recovery selects the most recent exact URL when a path recurs', () => {
  const tab = makeTab();
  loadPage(tab, componentPage({ search: '?filter=Cold', scrollY: 100 })).firePagehide();
  loadPage(tab, areaPage()).firePagehide();
  loadPage(tab, componentPage({ search: '?filter=Other', scrollY: 200 })).firePagehide();
  loadPage(tab, evidencePage()).firePagehide();
  loadPage(tab, componentPage({ search: '?filter=Cold', scrollY: 800 })).firePagehide();
  loadPage(tab, archPage()).firePagehide();

  const back = loadPage(tab, componentPage({ search: '?filter=Cold', navType: 'back_forward' }));
  assert.equal(back.error, null);
  assert.equal(tab.lastScrollTo, 800, 'the newest exact URL wins over older visits and other filters');
  assert.equal(back.stack().length, 4, 'only the recovered visit and later views leave the return trail');
  assert.equal(back.pillWhere(), 'Evidence');
  assert.equal(back.restore(), null);
});

test('a cold traversal cannot restore a card from a different filter or fragment', () => {
  for (const changed of [{ search: '?filter=Other' }, { hash: '#other' }]) {
    const tab = makeTab();
    const card = makeDetails('component-cold_reader_route_map');
    card.open = true;
    loadPage(tab, componentPage({
      search: '?filter=Cold+Reader', scrollY: 1166, openDetails: [card],
    })).firePagehide();
    loadPage(tab, areaPage()).firePagehide();
    const incomingCard = makeDetails(card.id);
    const back = loadPage(tab, componentPage({
      search: '?filter=Cold+Reader', ...changed, navType: 'back_forward',
      openDetails: [incomingCard],
    }));
    assert.equal(back.error, null);
    assert.equal(incomingCard.open, false);
    assert.equal(tab.lastScrollTo, undefined, 'another URL cannot supply a reading position');
    assert.equal(back.restore(), null);
  }
});

test('cold history restoration preserves explicit return precedence and ignores ordinary forward clicks', () => {
  const tab = makeTab();
  loadPage(tab, archPage({ scrollY: 300 })).firePagehide();
  loadPage(tab, areaPage()).firePagehide();
  const forward = loadPage(tab, archPage({ navType: 'navigate' }));
  assert.equal(tab.lastScrollTo, undefined, 'a normal forward click never consumes a historical snapshot');
  assert.equal(forward.stack().length, 2);

  tab.store.setItem('mc:viewstate:restore', JSON.stringify({
    path: '/docs/architecture.html', url: '/docs/architecture.html',
    y: 850, open: [], focus: null,
  }));
  const back = loadPage(tab, archPage({ navType: 'back_forward' }));
  assert.equal(tab.lastScrollTo, 850, 'an existing explicit restore wins over the historical snapshot');
  assert.equal(back.restore(), null);
});

test('BFCache pageshow leaves live disclosure and scroll state with the browser', () => {
  const tab = makeTab();
  const card = makeDetails('component-cold_reader_route_map');
  const page = loadPage(tab, componentPage({ scrollY: 440, openDetails: [card] }));
  tab.store.setItem('mc:viewstate:stack', JSON.stringify([
    { path: '/docs/components.html', url: '/docs/components.html', title: 'Components',
      y: 1166, open: [card.id], focus: null },
  ]));
  page.firePageshow(true);
  assert.equal(card.open, false, 'cached live state is not overwritten by an older snapshot');
  assert.equal(tab.lastScrollTo, undefined);
  assert.equal(page.win.pageYOffset, 440);
  assert.equal(page.restore(), null, 'BFCache traversal does not leave a stale pending restore');
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


test('glossary preview payload waits for idle before warming', () => {
  const idle = [];
  const term = makeLink('glossary.html#glossary-system', 'idle-system');
  term.className = 'narrative-ref--term';
  term.setAttribute('data-term', 'system');
  const page = loadPage(makeTab(), hubPage({
    bodyChildren: [term], links: [term],
    windowGlobals: { requestIdleCallback(fn) { idle.push(fn); } },
  }));
  assert.equal(page.error, null);
  assert.equal(page.doc.head.querySelector('script[data-term-previews]'), null);
  assert.equal(page.doc.querySelector('.term-tip'), null);
  idle.forEach((fn) => fn({ timeRemaining: () => 8 }));
  assert.ok(page.doc.head.querySelector('script[data-term-previews]'));
});

function loadSearchFixture({ deferred = false, url = 'glossary.html#glossary-component', recordCount = 1, execCommand = () => true } = {}) {
  const opener = makeEl('button'); opener.setAttribute('data-search-open', '');
  const modal = makeEl('div'); modal.setAttribute('data-search-modal', ''); modal.setAttribute('hidden', '');
  const input = makeEl('input'); input.setAttribute('data-search-input', '');
  const list = makeEl('ul'); list.setAttribute('data-search-results', '');
  const count = makeEl('p'); count.setAttribute('data-search-count', '');
  const empty = makeEl('p'); empty.setAttribute('data-search-empty', '');
  const closer = makeEl('button'); closer.setAttribute('data-search-close', '');
  [input, closer, list, count, empty].forEach(el => modal.appendChild(el));
  const tab = makeTab();
  const records = Array.from({ length: recordCount }, (_, i) => ({ kind: 'page', label: 'Component ' + i, url, text: 'A glossary definition' }));
  const page = loadPage(tab, {
    path: '/docs/glossary.html', active: opener, bodyChildren: [opener, modal], execCommand,
    windowGlobals: deferred ? {} : { __MICROCOSM_INDEX__: { records } },
  });
  assert.equal(page.error, null);
  opener.dispatch('click');
  return { ...page, tab, opener, modal, input, list, count, records };
}

test('Escape dismisses search from a result action and returns focus to the opener', () => {
  const page = loadSearchFixture();
  assert.equal(page.modal.hidden, false);
  const action = page.list.querySelector('.cmdk__action');
  assert.ok(action, 'search renders a secondary result action');
  page.doc.activeElement = action;
  let prevented = false;
  page.modal.dispatch('keydown', { key: 'Escape', target: action, preventDefault() { prevented = true; } });
  assert.ok(prevented);
  assert.equal(page.modal.hidden, true);
  assert.equal(page.body.classList.contains('cmdk-open'), false);
  assert.equal(page.opener._focused, true);
  assert.equal(page.input.getAttribute('aria-expanded'), 'false');
});

test('following an in-page search result removes the overlay and scroll lock before navigation', () => {
  const page = loadSearchFixture();
  page.input.dispatch('keydown', { key: 'Enter', preventDefault() {} });
  assert.match(page.tab.pendingHref, /glossary\.html#glossary-component$/);
  assert.equal(page.modal.hidden, true);
  assert.equal(page.body.classList.contains('cmdk-open'), false);
});

test('a search index arriving after dismissal does not reactivate the hidden combobox', () => {
  const page = loadSearchFixture({ deferred: true });
  assert.match(page.doc.querySelector('[data-search-empty]').textContent, /Loading/);
  page.modal.dispatch('keydown', { key: 'Escape', preventDefault() {} });
  page.win.__MICROCOSM_INDEX__ = { records: page.records };
  const script = page.doc.head.querySelector('script[data-search-index]');
  assert.ok(script);
  script.dispatch('load');
  assert.equal(page.modal.hidden, true);
  assert.equal(page.input.getAttribute('aria-expanded'), 'false');
  assert.equal(page.input.getAttribute('aria-activedescendant'), null);
  page.opener.dispatch('click');
  assert.equal(page.list.children.length, 1, 'the loaded index is usable on reopening');
});

test('contents tracking keeps the preceding section active between distant headings', () => {
  const toc = makeEl('nav'); toc.className = 'docs-toc';
  const first = makeLink('#first'); const second = makeLink('#second');
  toc.appendChild(first); toc.appendChild(second);
  const h1 = makeEl('h2'); h1.id = 'first'; h1._docTop = 150;
  const h2 = makeEl('h2'); h2.id = 'second'; h2._docTop = 1000;
  const page = loadPage(makeTab(), {
    path: '/docs/guide.html', scrollY: 450,
    bodyChildren: [toc, h1, h2], byId: [h1, h2],
  });
  assert.equal(page.error, null);
  assert.equal(first.classList.contains('is-current'), true);
  assert.equal(first.getAttribute('aria-current'), 'location');
  page.win.pageYOffset = 1000;
  page.fireScroll();
  assert.equal(first.getAttribute('aria-current'), null);
  assert.equal(second.getAttribute('aria-current'), 'location');
  page.win.pageYOffset = 0;
  page.fireScroll();
  assert.equal(second.getAttribute('aria-current'), null, 'before the first section there is no stale location');
});


test('search count distinguishes the visible result limit from all matching records', () => {
  const page = loadSearchFixture({ recordCount: 45 });
  page.input.value = 'Component';
  page.input.dispatch('input');
  assert.equal(page.list.children.length, 30);
  assert.match(page.count.textContent, /^Showing 30 of 45 matches/);
});

test('confirming an input-method composition does not navigate to a search result', () => {
  const page = loadSearchFixture();
  let prevented = false;
  page.input.dispatch('keydown', { key: 'Enter', isComposing: true, preventDefault() { prevented = true; } });
  assert.equal(page.tab.pendingHref, null);
  assert.equal(page.modal.hidden, false);
  assert.equal(prevented, false);
});


test('cancelling input-method composition keeps the search dialog open', () => {
  const page = loadSearchFixture();
  let prevented = false;
  page.modal.dispatch('keydown', { key: 'Escape', isComposing: true, preventDefault() { prevented = true; } });
  assert.equal(page.modal.hidden, false);
  assert.equal(prevented, false);
});


test('contents tracking skips hidden sections and does no heading work while the rail is hidden', () => {
  const toc = makeEl('nav'); toc.className = 'docs-toc';
  const first = makeLink('#first'); const hidden = makeLink('#hidden'); const next = makeLink('#next');
  [first, hidden, next].forEach(link => toc.appendChild(link));
  const h1 = makeEl('h2'); h1.id = 'first'; h1._docTop = 100;
  const h2 = makeEl('h2'); h2.id = 'hidden'; h2.hidden = true; h2._docTop = 0;
  const h3 = makeEl('h2'); h3.id = 'next'; h3._docTop = 900;
  const page = loadPage(makeTab(), { path: '/docs/guide.html', scrollY: 300, bodyChildren: [toc, h1, h2, h3], byId: [h1, h2, h3] });
  assert.equal(page.error, null);
  assert.equal(first.getAttribute('aria-current'), 'location');
  assert.equal(hidden.getAttribute('aria-current'), null);
  toc.hidden = true;
  let reads = 0;
  h1.getBoundingClientRect = () => { reads++; return { top: 0 }; };
  page.fireScroll();
  assert.equal(reads, 0, 'phone layouts do not measure an invisible contents rail');
});


test('the final short section becomes current at the end of the page', () => {
  const toc = makeEl('nav'); toc.className = 'docs-toc';
  const first = makeLink('#first'); const final = makeLink('#final');
  toc.appendChild(first); toc.appendChild(final);
  const h1 = makeEl('h2'); h1.id = 'first'; h1._docTop = 100;
  const h2 = makeEl('h2'); h2.id = 'final'; h2._docTop = 1000;
  const page = loadPage(makeTab(), { path: '/docs/guide.html', scrollY: 0, bodyChildren: [toc, h1, h2], byId: [h1, h2] });
  page.doc.documentElement.scrollHeight = 1500;
  page.win.innerHeight = 900;
  page.win.pageYOffset = 600;
  page.fireScroll();
  assert.equal(final.getAttribute('aria-current'), 'location');
  assert.equal(first.getAttribute('aria-current'), null);
});


for (const clipboardFails of [false, true]) {
  test('copying a search result restores focus and removes its proxy' + (clipboardFails ? ' on clipboard failure' : ''), () => {
    const page = loadSearchFixture({ execCommand: () => {
      if (clipboardFails) throw new Error('Clipboard unavailable');
      return true;
    } });
    const action = page.list.querySelector('.cmdk__action');
    page.doc.activeElement = action;
    action.dispatch('click', { currentTarget: action, stopPropagation() {} });
    assert.equal(page.doc.querySelector('.copy-proxy'), null);
    assert.equal(action._focused, true);
    assert.equal(action._focusPreventScroll, true);
    assert.equal(page.modal.hidden, false);
  });
}


test('repeated intent on the same term reuses the preview without layout or markup work', () => {
  const term = makeLink('glossary.html#glossary-system');
  term.className = 'narrative-ref--term';
  term.setAttribute('data-term', 'system'); term.setAttribute('data-term-label', 'System');
  term.setAttribute('data-term-preview', 'A system is a set of connected parts.');
  const page = loadPage(makeTab(), hubPage({ bodyChildren: [term], links: [term] }));
  page.doc.dispatch('mouseover', { target: term });
  const tip = page.doc.querySelector('.term-tip');
  assert.equal(tip.hidden, false);
  let layouts = 0;
  term.getBoundingClientRect = () => { layouts++; return { top: 50, left: 0, bottom: 70, width: 40, height: 20 }; };
  const textNode = tip.querySelector('.term-tip__text');
  const marker = makeEl('span'); marker.textContent = 'retained'; textNode.appendChild(marker);
  page.doc.dispatch('focusin', { target: term });
  assert.equal(layouts, 0);
  assert.equal(textNode.children.includes(marker), true);
});

test('moving between term previews clears the old description association', () => {
  const terms = ['system', 'component'].map(key => {
    const term = makeLink('glossary.html#glossary-' + key);
    term.className = 'narrative-ref--term'; term.setAttribute('data-term', key);
    term.setAttribute('data-term-preview', 'Definition of ' + key); return term;
  });
  const page = loadPage(makeTab(), hubPage({ bodyChildren: terms, links: terms }));
  page.doc.dispatch('mouseover', { target: terms[0] });
  assert.equal(terms[0].getAttribute('aria-describedby'), 'mc-term-tip');
  page.doc.dispatch('mouseover', { target: terms[1] });
  assert.equal(terms[0].getAttribute('aria-describedby'), null);
  assert.equal(terms[1].getAttribute('aria-describedby'), 'mc-term-tip');
});

function coldNotationPage() {
  const first = makeEl('span'), second = makeEl('span'), elsewhere = makeEl('button');
  const page = loadPage(makeTab(), hubPage({ bodyChildren: [first, second, elsewhere] }));
  assert.equal(page.error, null);
  page.win.PlectisTermHelp.registerNotation(first, ['sum']);
  page.win.PlectisTermHelp.registerNotation(second, ['product']);
  function focus(target) {
    const previous = page.doc.activeElement;
    page.doc.activeElement = target;
    if (previous) page.doc.dispatch('focusout', { target: previous, relatedTarget: target });
    page.doc.dispatch('focusin', { target, relatedTarget: previous });
  }
  function activate(target) {
    focus(target);
    page.doc.dispatch('keydown', { key: 'Enter', target, preventDefault() {}, stopImmediatePropagation() {} });
  }
  function deliver() {
    page.win.__MICROCOSM_TERM_PREVIEWS__ = { terms: [
      { object_id: 'term:sum', preferred_label: 'Sum', reader_preview: 'Adds terms.', reader_card: 'The longer sum definition.' },
      { object_id: 'term:product', preferred_label: 'Product', reader_preview: 'Multiplies terms.', reader_card: 'The longer product definition.' },
    ] };
    page.doc.head.querySelector('script[data-term-previews]').dispatch('load', {});
    return page.doc.querySelector('.term-tip');
  }
  return { page, first, second, elsewhere, focus, activate, deliver };
}

test('cold notation Escape cancels activation before the glossary response', () => {
  const state = coldNotationPage();
  state.activate(state.first);
  state.page.doc.dispatch('keydown', { key: 'Escape', target: state.first });
  const tip = state.deliver();
  assert.ok(!tip || tip.hidden, 'a late glossary response must not reopen dismissed help');
});

test('cold notation activation is cancelled when focus leaves before load', () => {
  const state = coldNotationPage();
  state.activate(state.first);
  state.focus(state.elsewhere);
  const tip = state.deliver();
  assert.ok(!tip || tip.hidden, 'a late response must not steal the departed focus intent');
});

test('cold notation activation must not transfer to a newly focused formula', () => {
  const state = coldNotationPage();
  state.activate(state.first);
  state.focus(state.second);
  const tip = state.deliver();
  assert.equal(tip.hidden, false);
  assert.equal(tip.querySelector('.term-tip__label').textContent, 'Product');
  assert.equal(tip.classList.contains('is-expanded'), false, 'focus alone previews the second formula without activating it');
});

test('cold notation activation still expands when its focus intent remains current', () => {
  const state = coldNotationPage();
  state.activate(state.first);
  const tip = state.deliver();
  assert.equal(tip.hidden, false);
  assert.equal(tip.querySelector('.term-tip__label').textContent, 'Sum');
  assert.equal(tip.classList.contains('is-expanded'), true);
});

test('cold notation keyboard activation does not transfer to a different pointer target', () => {
  const state = coldNotationPage();
  state.activate(state.first);
  state.second.matches = selector => selector === ':hover';
  state.page.doc.dispatch('mouseover', { target: state.second, relatedTarget: state.first });
  const tip = state.deliver();
  assert.equal(tip.hidden, false);
  assert.equal(tip.querySelector('.term-tip__label').textContent, 'Product');
  assert.equal(tip.classList.contains('is-expanded'), false);
});

test('cold notation pointer departure cancels its pending preview', () => {
  const state = coldNotationPage();
  state.page.doc.dispatch('mouseover', { target: state.first, relatedTarget: state.elsewhere });
  state.page.doc.dispatch('mouseout', { target: state.first, relatedTarget: state.elsewhere });
  const tip = state.deliver();
  assert.ok(!tip || tip.hidden);
});

test('wide notation keeps expression arrow scrolling while its popup controls cycle symbols', () => {
  const math = makeEl('span');
  math.setAttribute('data-math-scroll', 'true');
  const page = loadPage(makeTab(), hubPage({
    bodyChildren: [math],
    windowGlobals: { __MICROCOSM_TERM_PREVIEWS__: { terms: [
      { object_id: 'term:sum', preferred_label: 'Sum', reader_preview: 'Adds terms.' },
      { object_id: 'term:product', preferred_label: 'Product', reader_preview: 'Multiplies terms.' },
    ] } },
  }));
  assert.equal(page.error, null);
  page.win.PlectisTermHelp.registerNotation(math, ['sum', 'product']);
  page.doc.activeElement = math;
  page.doc.dispatch('focusin', { target: math });
  const tip = page.doc.querySelector('.term-tip');
  assert.ok(tip.querySelector('.term-tip__cue').textContent.includes('Use Previous/Next for another symbol'));
  for (const key of ['ArrowLeft', 'ArrowRight']) {
    let prevented = false;
    page.doc.dispatch('keydown', { key, target: math, preventDefault() { prevented = true; } });
    assert.equal(prevented, false, 'native horizontal scrolling must keep the key default');
    assert.equal(tip.querySelector('.term-tip__label').textContent, 'Sum');
  }
  const previous = queryAll(tip, '.term-tip__back').find(el => el.textContent === 'Previous notation');
  const next = queryAll(tip, '.term-tip__back').find(el => el.textContent === 'Next notation');
  assert.equal(previous.hidden, false);
  assert.equal(next.hidden, false);
  next.dispatch('click', {});
  assert.equal(tip.querySelector('.term-tip__label').textContent, 'Product');
  previous.dispatch('click', {});
  assert.equal(tip.querySelector('.term-tip__label').textContent, 'Sum');
  page.doc.activeElement = next;
  let popupPrevented = false;
  page.doc.dispatch('keydown', { key: 'ArrowRight', target: next, preventDefault() { popupPrevented = true; } });
  assert.equal(popupPrevented, true, 'popup buttons retain keyboard notation cycling');
  assert.equal(tip.querySelector('.term-tip__label').textContent, 'Product');
});

function notationOverlayPage() {
  const math = makeEl('span');
  const under = makeLink('glossary.html#glossary-system', 'underlying-system');
  under.className = 'narrative-ref--term'; under.setAttribute('data-term', 'system');
  const page = loadPage(makeTab(), hubPage({
    bodyChildren: [math, under], links: [under],
    windowGlobals: { __MICROCOSM_TERM_PREVIEWS__: { terms: [
      { object_id: 'term:sum', preferred_label: 'Sum', reader_preview: 'Adds terms.' },
      { object_id: 'term:product', preferred_label: 'Product', reader_preview: 'Multiplies terms.' },
      { object_id: 'term:system', preferred_label: 'System', reader_preview: 'Connected parts.' },
    ] } },
  }));
  assert.equal(page.error, null);
  page.win.PlectisTermHelp.registerNotation(math, ['sum', 'product']);
  page.doc.dispatch('mouseover', { target: math });
  const tip = page.doc.querySelector('.term-tip');
  const next = queryAll(tip, '.term-tip__back').find(el => el.textContent === 'Next notation');
  page.page.hitTarget = under;
  return { page, math, under, tip, next };
}

test('expanded notation popup keeps control intent when another term lies underneath', () => {
  const { page, math, tip, next } = notationOverlayPage();
  page.doc.dispatch('click', { target: math, button: 0, preventDefault() {} });
  assert.equal(tip.classList.contains('is-expanded'), true);
  tip.dispatch('mouseenter', { target: tip, clientX: 50, clientY: 50 });
  tip.dispatch('mousemove', { target: next, clientX: 50, clientY: 50 });
  next.dispatch('click', {});
  assert.equal(tip.querySelector('.term-tip__label').textContent, 'Product');
  assert.equal(tip.classList.contains('is-expanded'), true);
});

test('passive notation action buttons keep their target while other passive preview space can retarget', () => {
  const { page, tip, next, under } = notationOverlayPage();
  // Mouseenter targets the popup itself: hit-test with pointer events enabled
  // first to see whether its actual action button is under the pointer.
  page.doc.elementFromPoint = () => tip.style.pointerEvents === 'none' ? under : next;
  tip.dispatch('mouseenter', { target: tip, clientX: 50, clientY: 50 });
  tip.dispatch('mousemove', { target: next, clientX: 50, clientY: 50 });
  next.dispatch('click', {});
  assert.equal(tip.querySelector('.term-tip__label').textContent, 'Product');
  // Blank passive-card space still discovers a different term behind the card.
  page.doc.elementFromPoint = () => under;
  tip.dispatch('mousemove', { target: tip, clientX: 50, clientY: 50 });
  assert.equal(tip.querySelector('.term-tip__label').textContent, 'System');
});

test('focused passive notation controls retain their target during pointer movement', () => {
  const { page, tip, next } = notationOverlayPage();
  page.doc.activeElement = next;
  tip.dispatch('mousemove', { target: tip, clientX: 50, clientY: 50 });
  assert.equal(tip.querySelector('.term-tip__label').textContent, 'Sum');
  next.dispatch('click', {});
  assert.equal(tip.querySelector('.term-tip__label').textContent, 'Product');
  assert.equal(tip.classList.contains('is-expanded'), false);
});

test('expanded definitions retain their core meaning without repeating an included preview', () => {
  const cases = [
    { reader_preview: 'A lemniscate is a figure-eight curve.', reader_card: 'The term is also used for related curves.',
      expected: 'A lemniscate is a figure-eight curve. The term is also used for related curves.' },
    { reader_preview: 'A curve.', reader_card: 'A curve.', expected: 'A curve.' },
    { reader_preview: 'A curve.', reader_card: 'A curve. More detail.', expected: 'A curve. More detail.' },
    { text: 'A <curve> & its points.', reader_card: 'More detail.', expected: 'A <curve> & its points. More detail.' },
  ];
  for (const row of cases) {
    const math = makeEl('span');
    const page = loadPage(makeTab(), hubPage({
      bodyChildren: [math],
      windowGlobals: { __MICROCOSM_TERM_PREVIEWS__: { terms: [
        { object_id: 'term:curve', preferred_label: 'Curve', ...row },
      ] } },
    }));
    assert.equal(page.error, null);
    page.win.PlectisTermHelp.registerNotation(math, ['curve']);
    page.doc.dispatch('click', { target: math, button: 0, preventDefault() {} });
    const text = page.doc.querySelector('.term-tip__text');
    assert.equal(text.textContent, row.expected);
    assert.equal(text.querySelector('curve'), null, 'definition text remains escaped');
  }
});


function glossaryFilterFixture(overrides = {}) {
  const toolbar = makeEl('div');
  toolbar.setAttribute('data-comp-filter', '');
  toolbar.setAttribute('data-comp-filter-items', '.term-card');
  toolbar.setAttribute('data-comp-count-label', 'terms');
  toolbar.setAttribute('hidden', '');
  const input = makeEl('input');
  input.id = 'comp-filter-input';
  const status = makeEl('p');
  status.id = 'comp-filter-status';
  toolbar.appendChild(input);
  toolbar.appendChild(status);
  const empty = makeEl('p');
  empty.setAttribute('data-comp-empty', '');
  empty.setAttribute('hidden', '');
  const clear = makeEl('button');
  clear.setAttribute('data-comp-clear', '');
  empty.appendChild(clear);
  const alpha = makeDetails('glossary-alpha');
  alpha.className = 'dcard term-card';
  alpha.setAttribute('data-search', 'Alpha first letter α');
  const beta = makeDetails('glossary-beta');
  beta.className = 'dcard term-card';
  beta.setAttribute('data-search', 'Beta second letter β');
  for (const card of [alpha, beta]) card.appendChild(makeEl('summary'));
  const unrelated = makeEl('li');
  unrelated.className = 'comp-item';
  unrelated.setAttribute('data-search', 'unrelated');
  return {
    toolbar, input, status, empty, clear, alpha, beta, unrelated,
    page: {
      path: '/docs/glossary.html', title: 'Glossary',
      bodyChildren: [toolbar, empty, alpha, beta, unrelated],
      byId: [input, status, alpha, beta], openDetails: [alpha, beta],
      ...overrides,
    },
  };
}

test('glossary opt-in reuses filtering, truthful counts, URL state, Escape and empty-state clear', () => {
  const tab = makeTab();
  const f = glossaryFilterFixture({ search: '?from=paper&filter=%CE%B1' });
  const page = loadPage(tab, f.page);
  assert.equal(page.error, null);
  assert.equal(f.toolbar.hidden, false);
  assert.equal(f.input.value, 'α');
  assert.equal(f.alpha.hidden, false);
  assert.equal(f.beta.hidden, true);
  assert.equal(f.unrelated.hidden, false, 'the opt-in selector owns only term cards');
  assert.equal(f.status.textContent, '1 of 2 shown');
  const state = { external: 'preserve' };
  page.win.history.state = state;
  f.input.value = 'No such term';
  f.input.dispatch('input');
  assert.equal(f.status.textContent, '0 of 2 shown');
  assert.equal(f.empty.hidden, false);
  assert.equal(new URLSearchParams(page.loc.search).get('filter'), 'No such term');
  assert.equal(new URLSearchParams(page.loc.search).get('from'), 'paper');
  assert.equal(page.win.history.state, state);
  f.clear.dispatch('click');
  assert.equal(f.input.value, '');
  assert.equal(f.input._focused, true);
  assert.equal(f.status.textContent, '2 terms');
  assert.equal(f.empty.hidden, true);
  f.input.value = 'beta';
  f.input.dispatch('input');
  assert.equal(f.alpha.hidden, true);
  f.input.dispatch('keydown', { key: 'Escape' });
  assert.equal(f.alpha.hidden, false);
  assert.equal(f.input.value, '');
  assert.equal(page.loc.search, '?from=paper');
});

test('fresh glossary fragment arrivals reveal conflicting targets and retain matching filters', () => {
  for (const query of ['alpha', 'beta']) {
    const f = glossaryFilterFixture({ search: '?filter=' + query, hash: '#glossary-beta' });
    const page = loadPage(makeTab(), f.page);
    assert.equal(page.error, null);
    assert.equal(f.beta.hidden, false);
    assert.equal(f.beta.open, true);
    assert.equal(f.input.value, query === 'beta' ? 'beta' : '');
    assert.equal(page.loc.hash, '#glossary-beta');
  }
});

test('typing a glossary filter does not treat the old URL fragment as a new navigation', () => {
  const f = glossaryFilterFixture({ hash: '#glossary-beta' });
  const page = loadPage(makeTab(), f.page);
  f.input.value = 'alpha';
  f.input.dispatch('input');
  assert.equal(f.beta.hidden, true);
  assert.equal(f.input.value, 'alpha');
  assert.equal(page.loc.search, '?filter=alpha');
  assert.equal(page.loc.hash, '#glossary-beta');
});

test('following the same glossary fragment reveals a filtered-out term before its native jump', () => {
  const f = glossaryFilterFixture({ hash: '#glossary-beta' });
  const page = loadPage(makeTab(), f.page);
  f.input.value = 'alpha';
  f.input.dispatch('input');
  assert.equal(f.beta.hidden, true);
  const link = makeLink('#glossary-beta');
  page.doc.dispatch('click', { target: link, button: 0 });
  assert.equal(f.input.value, '');
  assert.equal(f.beta.hidden, false);
  assert.equal(f.beta.open, true);
  assert.equal(page.loc.search, '');
});

test('glossary hash navigation reveals a filtered-out target without dropping other URL parameters', () => {
  const f = glossaryFilterFixture({ search: '?from=paper&filter=alpha' });
  const page = loadPage(makeTab(), f.page);
  page.loc.hash = '#glossary-beta';
  page.fireHashchange();
  assert.equal(f.input.value, '');
  assert.equal(f.beta.hidden, false);
  assert.equal(f.beta.open, true);
  assert.equal(page.loc.search, '?from=paper');
});

test('cold and explicit glossary returns keep a saved filter despite its old excluded fragment', () => {
  for (const exact of [false, true]) {
    const tab = makeTab();
    const entry = {
      path: '/docs/glossary.html', url: '/docs/glossary.html?filter=alpha#glossary-beta',
      title: 'Glossary', y: 1234, open: ['glossary-alpha'], focus: null,
    };
    tab.store.setItem(exact ? 'mc:viewstate:restore' : 'mc:viewstate:stack', JSON.stringify(exact ? entry : [entry]));
    const f = glossaryFilterFixture({ search: '?filter=alpha', hash: '#glossary-beta', navType: exact ? 'navigate' : 'back_forward' });
    const page = loadPage(tab, f.page);
    assert.equal(page.error, null);
    assert.equal(f.input.value, 'alpha');
    assert.equal(f.beta.hidden, true);
    assert.equal(f.alpha.hidden, false);
    assert.equal(f.alpha.open, true);
    assert.equal(page.loc.search, '?filter=alpha');
    assert.equal(tab.lastScrollTo, 1234);
  }
});

test('glossary popstate restores URL filtering without treating an old hash as a new target', () => {
  const f = glossaryFilterFixture();
  const page = loadPage(makeTab(), f.page);
  page.loc.search = '?filter=beta';
  page.loc.hash = '#glossary-alpha';
  page.firePopstate();
  assert.equal(f.input.value, 'beta');
  assert.equal(f.alpha.hidden, true);
  assert.equal(f.beta.hidden, false);
  assert.equal(f.status.textContent, '1 of 2 shown');
});


test('following a new glossary fragment preserves the prior filter entry for same-page Back', () => {
  const tab = makeTab();
  const timers = [];
  const f = glossaryFilterFixture({
    search: '?filter=alpha', hash: '#glossary-alpha',
    windowGlobals: { setTimeout(fn) { timers.push(fn); return timers.length; } },
  });
  const page = loadPage(tab, f.page);
  const link = makeLink('#glossary-beta');
  page.doc.dispatch('click', { target: link, button: 0 });
  assert.equal(f.beta.hidden, false, 'the target is visible before the native jump');
  assert.equal(page.loc.search, '?filter=alpha', 'the old history entry retains its filter');
  page.loc.hash = '#glossary-beta';
  page.win.history.state = null;
  page.firePopstate(null);
  page.fireHashchange();
  assert.equal(f.beta.hidden, false);
  assert.equal(f.input.value, '');
  assert.equal(page.loc.search, '', 'only the new history entry clears its filter');
  while (timers.length) timers.shift()();
  page.loc.search = '?filter=alpha';
  page.loc.hash = '#glossary-alpha';
  page.firePopstate();
  const callsBeforeTraversal = tab.scrollToCalls.length;
  page.fireHashchange();
  assert.equal(f.input.value, 'alpha');
  assert.equal(f.beta.hidden, true);
  assert.equal(page.loc.search, '?filter=alpha');
  assert.equal(tab.scrollToCalls.length, callsBeforeTraversal, 'fragment alignment cannot overwrite native restored scroll');
});


test('new visible glossary fragments still open and align after popstate, including scripted navigation', () => {
  for (const search of ['', '?filter=letter']) {
    for (const clicked of [true, false]) {
      const timers = [];
      const tab = makeTab();
      const f = glossaryFilterFixture({ search, windowGlobals: {
        setTimeout(fn) { timers.push(fn); return timers.length; },
      } });
      f.beta._docTop = 700;
      f.beta.children[0]._docTop = 700;
      const page = loadPage(tab, f.page);
      assert.equal(f.beta.open, false);
      if (clicked) page.doc.dispatch('click', { target: makeLink('#glossary-beta'), button: 0 });
      page.loc.hash = '#glossary-beta';
      page.win.history.state = null;
      page.firePopstate(null);
      page.fireHashchange();
      assert.equal(page.error, null);
      assert.equal(f.beta.hidden, false);
      assert.equal(f.beta.open, true);
      assert.equal(f.input.value, search ? 'letter' : '');
      assert.equal(page.loc.search, search);
      assert.ok(tab.scrollToCalls.length > 0, 'new fragments retain normal alignment');
    }
  }
});
