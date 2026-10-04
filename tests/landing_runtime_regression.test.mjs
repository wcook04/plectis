import { test } from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = dirname(fileURLToPath(import.meta.url));
const SITE = join(HERE, '..');
const HTML = readFileSync(join(SITE, 'index.html'), 'utf8');
const SOURCE = readFileSync(join(SITE, 'assets', 'landing.js'), 'utf8');

function runtimeRef(name, src) {
  const ref = { getAttribute: (key) => key === 'src' ? src : null };
  return {
    getAttribute: (key) => key === 'data-plectis-runtime' ? name : null,
    content: { querySelector: () => ref },
  };
}

function element(tag) {
  return {
    tagName: tag.toUpperCase(),
    _listeners: {},
    _attrs: {},
    setAttribute(key, value) { this._attrs[key] = String(value); },
    getAttribute(key) { return this._attrs[key] || null; },
    addEventListener(type, fn) { this._listeners[type] = fn; },
  };
}

function harness() {
  const frames = [];
  const idle = [];
  const preloads = [];
  const scripts = [];
  const roots = {};
  const refs = [
    runtimeRef('docs', 'assets/docs.js?v=docs'),
    runtimeRef('art', 'assets/art.js?v=art'),
  ];
  const document = {
    body: { appendChild(node) { scripts.push(node); } },
    head: { appendChild(node) { preloads.push(node); } },
    documentElement: { scrollTop: 0, getAttribute(key) { return roots[key] || null; }, setAttribute(key, value) { roots[key] = value; } },
    activeElement: null,
    title: 'Plectis',
    querySelectorAll(selector) {
      if (selector === 'template[data-plectis-runtime]') return refs;
      if (selector === 'details[open][id]') return [];
      return [];
    },
    querySelector() { return null; },
    getElementById() { return null; },
    createElement: element,
    addEventListener() {},
    removeEventListener() {},
  };
  const window = {
    location: { href: 'https://example.test/', origin: 'https://example.test', pathname: '/', search: '', hash: '' },
    pageYOffset: 0,
    scrollTo() {},
    requestAnimationFrame(fn) { frames.push(fn); },
    requestIdleCallback(fn) { idle.push(fn); },
    setTimeout(fn) { fn(); },
    addEventListener() {},
    sessionStorage: { getItem() { return null; }, setItem() {} },
  };
  const context = {
    document,
    window,
    navigator: {},
    URL,
    Event,
  };
  vm.runInNewContext(SOURCE, context, { filename: 'landing.js' });
  return { frames, idle, preloads, scripts, roots };
}

test('landing bands stay open and never fold behind chevrons', () => {
  // 2026-10-03. Will, on the folded bands: they "didn't make any sense, and
  // nobody's going to read them". Every band on the front door is open; only
  // the video transcripts fold.
  assert.doesNotMatch(SOURCE, /collapsedBands/);
  assert.doesNotMatch(SOURCE, /stayOpen/);
  assert.doesNotMatch(HTML, /data-landing-expand/);
  assert.doesNotMatch(HTML, /<details class="fold"/);
});

test('landing keeps heavyweight runtimes inert behind the small scheduler', () => {
  assert.match(HTML, /<template data-plectis-runtime="docs"><script src="assets\/docs\.js\?v=/);
  assert.match(HTML, /<template data-plectis-runtime="art"><script src="assets\/art\.js\?v=/);
  assert.match(HTML, /<template data-plectis-runtime="universe"><script src="maths\/assets\/universe\.js\?v=/);
  assert.match(HTML, /<script async src="assets\/landing\.js\?v=/);
  assert.doesNotMatch(HTML, /<script async src="assets\/(?:docs|art)\.js/);
  // In-page jumps ease in and out; a long jump lands 240px short and glides
  // the last stretch, easing out (critique, 4 Oct 2026).
  assert.match(SOURCE, /var eased = glide \? 1 - Math\.pow\(1 - p, 3\) :\s*\(p < 0\.5 \? 4 \* p \* p \* p : 1 - Math\.pow\(-2 \* p \+ 2, 3\) \/ 2\);/);
  assert.match(SOURCE, /window\.cancelAnimationFrame\(anchorRaf\)/);
});

test('runtime startup crosses a paint barrier and serializes docs before art', () => {
  const page = harness();
  assert.equal(page.preloads.length, 2, 'both runtimes warm without executing');
  assert.equal(page.scripts.length, 0, 'no runtime activates during scheduler evaluation');
  assert.equal(page.frames.length, 1, 'first paint barrier is queued');

  page.frames.shift()();
  assert.equal(page.scripts.length, 0, 'first animation frame still does no runtime work');
  page.frames.shift()();
  assert.equal(page.idle.length, 1, 'docs waits for an idle slot after paint');
  page.idle.shift()({ didTimeout: false, timeRemaining: () => 8 });
  assert.equal(page.scripts.length, 1);
  assert.match(page.scripts[0].src, /docs\.js/);
  assert.equal(page.roots['data-plectis-docs-runtime'], 'loading');

  page.scripts[0]._listeners.load();
  assert.equal(page.roots['data-plectis-docs-runtime'], 'ready');
  assert.equal(page.idle.length, 1, 'art is queued only after docs settles');
  page.idle.shift()({ didTimeout: false, timeRemaining: () => 8 });
  assert.equal(page.scripts.length, 2);
  assert.match(page.scripts[1].src, /art\.js/);
});

/* The map band (2026-10-04): one slice, two drawings, moved by a switch or the
   edge arrows. These run the production block against a small fake DOM. */
function atlasHarness({ reduced = false, hash = '' } = {}) {
  const start = SOURCE.indexOf('/* The map band (2026-10-04).');
  assert.ok(start > 0, 'the map band block is present');
  const block = SOURCE.slice(start);
  const events = [];
  const timers = [];
  const frames = [];
  const listeners = {};
  const classList = (owner) => {
    const set = new Set();
    return {
      add: (n) => set.add(n), remove: (n) => set.delete(n), contains: (n) => set.has(n),
      toggle: (n, on) => { const want = on === undefined ? !set.has(n) : !!on; if (want) set.add(n); else set.delete(n); return want; },
      _set: set,
    };
  };
  const node = (attrs = {}) => {
    const el = {
      _attrs: { ...attrs }, _on: {}, style: {}, hidden: true, tabIndex: 0, inert: false, animations: [],
      getAttribute(k) { return k in this._attrs ? this._attrs[k] : null; },
      setAttribute(k, v) { this._attrs[k] = String(v); },
      removeAttribute(k) { delete this._attrs[k]; },
      addEventListener(type, fn) { (this._on[type] = this._on[type] || []).push(fn); },
      fire(type, event = {}) { (this._on[type] || []).forEach((fn) => fn({ target: this, preventDefault() {}, ...event })); },
      focus() { focused.el = this; },
      animate(keys, timing) { this.animations.push({ keys, timing }); return {}; },
    };
    el.classList = classList(el);
    return el;
  };
  const focused = { el: null };
  const figures = [node(), node()];
  const slides = ['mathematics', 'system'].map((view, i) => {
    const slide = node({ 'data-atlas-slide': view });
    slide.querySelector = (sel) => sel === '.home-split__figure' ? figures[i] : null;
    slide.closest = () => slide;
    return slide;
  });
  const tabs = ['mathematics', 'system'].map((view) => node({ 'data-atlas-go': view }));
  const prev = node();
  const next = node();
  const list = node({ role: 'tablist' });
  const viewport = node();
  viewport.scrollLeft = 120;
  const track = node();
  track.querySelectorAll = (sel) => sel === '[data-atlas-slide]' ? slides : [];
  const band = node();
  band.querySelector = (sel) => ({
    '.home-atlas__viewport': viewport, '[data-atlas-track]': track,
    '[data-atlas-prev]': prev, '[data-atlas-next]': next, '[role="tablist"]': list,
  })[sel] || null;
  band.querySelectorAll = (sel) => sel === '[data-atlas-go]' ? tabs : [];
  band.contains = (el) => slides.includes(el) || el === band;
  const document = {
    querySelector: (sel) => sel === '[data-atlas]' ? band : null,
    getElementById: (id) => id === 'system' ? slides[1] : id === 'mathematics' ? band : null,
    addEventListener: (type, fn) => { (listeners[type] = listeners[type] || []).push(fn); },
    dispatchEvent: (event) => { events.push({ type: event.type, detail: event.detail }); (listeners[event.type] || []).forEach((fn) => fn(event)); },
  };
  const replaced = [];
  const window = {
    location: { hash },
    matchMedia: (q) => ({ matches: q.includes('reduce') ? reduced : q.includes('hover') }),
    requestAnimationFrame: (fn) => frames.push(fn),
    setTimeout: (fn, ms) => { timers.push({ fn, ms }); return timers.length; },
    clearTimeout: () => {},
    history: { state: null, replaceState: (s, t, url) => replaced.push(url) },
    addEventListener: () => {},
  };
  class FakeElement {}
  FakeElement.prototype.animate = function () {};
  vm.runInNewContext(block, {
    document, window, Element: FakeElement,
    CustomEvent: class { constructor(type, init) { this.type = type; this.detail = init && init.detail; } },
  }, { filename: 'landing.js#atlas' });
  const flush = () => { while (frames.length) frames.shift()(); while (timers.length) timers.shift().fn(); };
  return { band, track, slides, tabs, prev, next, list, viewport, figures, events, flush, replaced, focused };
}

test('the map band starts on the mathematics with the system slide inert', () => {
  const page = atlasHarness();
  assert.ok(page.band.classList.contains('is-live'));
  assert.equal(page.viewport.scrollLeft, 0, 'a fragment that scrolled the fallback strip is undone');
  assert.equal(page.band.getAttribute('data-atlas-view'), 'mathematics');
  assert.equal(page.slides[0].inert, false);
  assert.equal(page.slides[1].inert, true);
  assert.equal(page.slides[1].getAttribute('aria-hidden'), 'true');
  assert.deepEqual(page.tabs.map((t) => t.getAttribute('aria-selected')), ['true', 'false']);
  assert.deepEqual(page.tabs.map((t) => t.tabIndex), [0, -1]);
  assert.ok(page.prev.classList.contains('is-away') && !page.next.classList.contains('is-away'));
  assert.match(page.track.style.transform, /translate3d\(calc\(0% \+ 0px\)/);
});

test('a click on System moves the whole slice once, eased, and asks for its drawing', () => {
  const page = atlasHarness();
  page.tabs[1].fire('click');
  assert.match(page.track.style.transform, /calc\(-100% \+ 0px\)/);
  assert.ok(!page.band.classList.contains('is-instant'), 'a click plays the move');
  assert.equal(page.slides[0].inert, true, 'the leaving slide stops taking focus at once');
  assert.equal(page.slides[1].inert, false);
  assert.ok(page.slides[0].classList.contains('is-shown') && page.slides[1].classList.contains('is-shown'),
    'both slides paint while the slice moves');
  assert.equal(page.figures[0].animations.length, 1, 'the leaving drawing rides the nearer layer');
  assert.equal(page.figures[1].animations.length, 1, 'the arriving drawing settles into place');
  assert.equal(page.figures[1].animations[0].timing.duration, 720);
  assert.ok(page.events.some((e) => e.type === 'plectis:runtime' && e.detail.name === 'system'));
  assert.ok(page.events.some((e) => e.type === 'plectis:atlas' && e.detail.phase === 'start' && e.detail.view === 'system'));
  assert.deepEqual(page.replaced, ['#system']);
  page.flush();
  assert.ok(!page.slides[0].classList.contains('is-shown'), 'the slide out of view stops painting once settled');
  assert.ok(page.events.some((e) => e.type === 'plectis:atlas' && e.detail.phase === 'end' && e.detail.view === 'system'));
  assert.ok(page.next.classList.contains('is-away') && !page.prev.classList.contains('is-away'));
});

test('arrow keys on the switch land at once, and reduced motion never animates', () => {
  const page = atlasHarness();
  page.list.fire('keydown', { key: 'ArrowRight' });
  assert.ok(page.band.classList.contains('is-instant'), 'a keyboard action never waits on an animation');
  assert.equal(page.figures[1].animations.length, 0);
  assert.equal(page.focused.el, page.tabs[1]);
  page.flush();
  page.list.fire('keydown', { key: 'Home' });
  assert.equal(page.band.getAttribute('data-atlas-view'), 'mathematics');

  const still = atlasHarness({ reduced: true });
  assert.ok(still.band.classList.contains('is-still'));
  still.tabs[1].fire('click');
  assert.ok(still.band.classList.contains('is-instant'));
  assert.equal(still.figures[0].animations.length + still.figures[1].animations.length, 0);
});

test('#system in the address opens the band on the system drawing without a move', () => {
  const page = atlasHarness({ hash: '#system' });
  assert.equal(page.band.getAttribute('data-atlas-view'), 'system');
  assert.ok(page.band.classList.contains('is-instant'));
  assert.equal(page.figures[1].animations.length, 0);
  assert.ok(page.events.some((e) => e.type === 'plectis:runtime' && e.detail.name === 'system'));
  assert.deepEqual(page.replaced, [], 'arriving by a link does not rewrite the address');
});
