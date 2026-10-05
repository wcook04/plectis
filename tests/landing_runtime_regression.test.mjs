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
  assert.equal(page.figures[1].animations[0].timing.duration, 620);
  assert.ok(page.band.classList.contains('is-moving'), 'the edge arrows step out while the slice moves');
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

test('map band and carousel buttons answer at once while docs.js is still loading', () => {
  // A button the landing runs itself must never be held for docs.js: on a
  // slow line the switch sat dead for seconds and then moved the band late.
  const listeners = {};
  const scripts = [];
  const refs = [
    runtimeRef('docs', 'assets/docs.js?v=docs'),
    runtimeRef('art', 'assets/art.js?v=art'),
  ];
  const document = {
    body: { appendChild(node) { scripts.push(node); } },
    head: { appendChild() {} },
    documentElement: { scrollTop: 0, getAttribute() { return null; }, setAttribute() {} },
    activeElement: null,
    title: 'Plectis',
    querySelectorAll(selector) { return selector === 'template[data-plectis-runtime]' ? refs : []; },
    querySelector() { return null; },
    getElementById() { return null; },
    createElement: element,
    addEventListener(type, fn, capture) { if (capture) listeners[type] = fn; },
    removeEventListener() {},
  };
  const window = {
    location: { href: 'https://example.test/', origin: 'https://example.test', pathname: '/', search: '', hash: '' },
    pageYOffset: 0, scrollTo() {}, requestAnimationFrame() {}, requestIdleCallback() {},
    setTimeout() {}, addEventListener() {}, sessionStorage: { getItem() { return null; }, setItem() {} },
  };
  vm.runInNewContext(SOURCE, { document, window, navigator: {}, URL, Event }, { filename: 'landing.js' });
  const click = (inside) => {
    let prevented = false;
    const button = {
      tagName: 'BUTTON',
      closest(sel) {
        if (sel === '[data-atlas], [data-results-carousel]') return inside ? {} : null;
        if (sel.includes('button')) return button;
        return null;
      },
      getAttribute() { return null; },
    };
    listeners.click({ target: button, button: 0, preventDefault() { prevented = true; }, stopImmediatePropagation() {} });
    return prevented;
  };
  assert.equal(click(true), false, 'a band or carousel control runs at once');
  assert.equal(scripts.length, 0, 'and does not wait on docs.js');
  assert.equal(click(false), true, 'other buttons still wait for the shared runtime');
});

test('the docs runtime never takes over the landing map band', () => {
  // docs.js carries an older carousel keyed on the same data-atlas names. On
  // the landing it disabled the band's back arrow (4 October 2026), so it must
  // pass over the band, which landing.js runs.
  const DOCS = readFileSync(join(SITE, 'assets', 'docs.js'), 'utf8');
  const start = DOCS.indexOf('(function initAtlasCarousel()');
  assert.ok(start > 0, 'the docs atlas carousel is present');
  const block = DOCS.slice(start, DOCS.indexOf('})();', start) + 5);
  const asked = [];
  const document = { querySelector(sel) { asked.push(sel); return null; } };
  vm.runInNewContext(block, { document, window: {} });
  assert.deepEqual(asked, ['[data-atlas]:not(.home-atlas)']);
  assert.match(HTML, /class="home-band home-maths home-atlas" id="mathematics" data-atlas/);
});

/* The glossary chip (5 October 2026): the open chip never stands on a
   drawing, and on a phone the folded mark steps aside once reading starts.
   These run the production cue against a small fake DOM, from landing.js and
   from docs.js's copy, which must stay in step. */
const DOCS_SOURCE = readFileSync(join(SITE, 'assets', 'docs.js'), 'utf8');
function cueBlock(source, closing, next) {
  const start = source.indexOf('/* Glossary cue (2026-09-14).');
  assert.ok(start >= 0, 'the glossary cue is present');
  const stop = source.indexOf(closing + next, start);
  assert.ok(stop > start, 'the glossary cue closes where expected');
  return source.slice(start, stop + closing.length);
}
const CUES = {
  'landing.js': cueBlock(SOURCE, '\n})();', '\n\n/* Results carousel'),
  'docs.js': cueBlock(DOCS_SOURCE, '\n  })();', '\n\n})();'),
};

function cueHarness(file, { width = 1512, height = 859, touch = false, narrow = false, drawings = [] } = {}) {
  const listeners = {};
  const queries = {};
  const classList = () => {
    const set = new Set();
    return {
      add: (n) => set.add(n), remove: (n) => set.delete(n), contains: (n) => set.has(n),
      toggle: (n, on) => { const want = on === undefined ? !set.has(n) : !!on; if (want) set.add(n); else set.delete(n); return want; },
    };
  };
  // The open chip and the folded mark as they stand at the window's lower
  // right, 16px in (style.css).
  const openBox = { left: width - 394, top: height - 99, right: width - 16, bottom: height - 16 };
  const markBox = { left: width - 58, top: height - 58, right: width - 16, bottom: height - 16 };
  const node = (tag) => {
    const el = {
      tagName: tag.toUpperCase(), children: [], _attrs: {}, _on: {}, style: {},
      setAttribute(k, v) { this._attrs[k] = String(v); },
      getAttribute(k) { return k in this._attrs ? this._attrs[k] : null; },
      appendChild(child) { this.children.push(child); child.parentNode = this; return child; },
      removeChild(child) { this.children = this.children.filter((c) => c !== child); child.parentNode = null; },
      addEventListener(type, fn) { (this._on[type] = this._on[type] || []).push(fn); },
      fire(type) { (this._on[type] || []).forEach((fn) => fn({ target: this })); },
    };
    el.classList = classList();
    el.getBoundingClientRect = () => (el.classList.contains('is-compact') && !el.classList.contains('is-open')) ? markBox : openBox;
    return el;
  };
  let hint = null;
  const attrs = {};
  const term = { getAttribute: (k) => k === 'href' ? 'docs/glossary.html#term-lean' : null };
  const document = {
    documentElement: { getAttribute: (k) => attrs[k] || null, setAttribute: (k, v) => { attrs[k] = v; } },
    body: { appendChild(child) { hint = child; child.parentNode = this; return child; }, removeChild() {} },
    createElement: node,
    createTextNode: (text) => ({ text }),
    querySelector: (sel) => sel === 'a.narrative-ref--term[data-term]' ? term : null,
    querySelectorAll: (sel) => sel === '[data-plait-band], .home-universe, .home-system' ? drawings : [],
    addEventListener() {},
    removeEventListener() {},
  };
  const window = {
    location: { pathname: '/' },
    scrollY: 0,
    innerWidth: width,
    innerHeight: height,
    matchMedia: (q) => (queries[q] = queries[q] || {
      matches: q.includes('hover: none') ? touch : q.includes('max-width: 620px') ? narrow : false,
      addEventListener() {},
    }),
    getComputedStyle: (el) => ({ visibility: el.visibility || 'visible' }),
    addEventListener: (type, fn) => { (listeners[type] = listeners[type] || []).push(fn); },
    removeEventListener: (type, fn) => { listeners[type] = (listeners[type] || []).filter((f) => f !== fn); },
    setTimeout: () => 0,
  };
  const localStorage = { getItem: () => null, setItem() {} };
  vm.runInNewContext(CUES[file], { document, window, localStorage }, { filename: file + '#glossary-cue' });
  assert.ok(hint, 'the cue mounted');
  const scrollTo = (y) => { window.scrollY = y; (listeners.scroll || []).forEach((fn) => fn()); };
  return { hint, mark: hint.children[0], scrollTo, attrs };
}

const card = (box, visibility) => ({
  visibility,
  getBoundingClientRect: () => ({ ...box, width: box.right - box.left, height: box.bottom - box.top }),
});

test('the open glossary chip folds to its mark where it would stand on a map', () => {
  // At 1512x859 and 1920x953 the mathematics map stands on the first screen
  // and the open chip covered its right edge (critique, 5 October 2026).
  const over = cueHarness('landing.js', { drawings: [card({ left: 734, top: 705, right: 1408, bottom: 1400 })] });
  assert.ok(over.hint.classList.contains('is-compact'), 'folded where it would cover the map');
  // On a monitor the map stands clear of the chip, which keeps its line.
  const clear = cueHarness('landing.js', { width: 2560, height: 1313, drawings: [card({ left: 1258, top: 810, right: 1933, bottom: 1504 })] });
  assert.ok(!clear.hint.classList.contains('is-compact'), 'open where nothing is under it');
  // The slide the switch has put away is hidden and does not count.
  const away = cueHarness('landing.js', { drawings: [card({ left: 734, top: 705, right: 1408, bottom: 1400 }, 'hidden')] });
  assert.ok(!away.hint.classList.contains('is-compact'), 'a hidden slide does not fold it');
});

test('a short first scroll that brings a map under the open chip folds it', () => {
  const box = { left: 734, top: 900, right: 1408, bottom: 1600 };
  const page = cueHarness('landing.js', { drawings: [card(box)] });
  assert.ok(!page.hint.classList.contains('is-compact'), 'open while the map is below it');
  box.top = 780;
  page.scrollTo(120);
  assert.ok(page.hint.classList.contains('is-compact'), 'folded once the map reaches it');
});

for (const file of Object.keys(CUES)) {
  test(`on a phone the mark steps aside once reading starts and stands again at the top (${file})`, () => {
    const page = cueHarness(file, { width: 390, height: 664, touch: true, narrow: true });
    assert.ok(page.hint.classList.contains('is-compact'), 'a touch screen starts on the mark');
    assert.ok(!page.hint.classList.contains('is-aside'), 'the mark stands at the top of the page');
    page.mark.fire('click');
    assert.ok(page.hint.classList.contains('is-open'), 'the mark opens the chip');
    page.scrollTo(300);
    assert.ok(page.hint.classList.contains('is-aside'), 'reading started: the mark steps aside');
    assert.ok(!page.hint.classList.contains('is-open'), 'and the chip it opened folds');
    page.scrollTo(0);
    assert.ok(!page.hint.classList.contains('is-aside'), 'back at the top it stands again');
    // A wider window keeps the mark wherever the reader is.
    const wide = cueHarness(file, { width: 1512, height: 859, touch: true, narrow: false });
    wide.scrollTo(3000);
    assert.ok(!wide.hint.classList.contains('is-aside'));
  });
}
