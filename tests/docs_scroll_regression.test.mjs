import { test } from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import { readFileSync } from 'node:fs';

const source = readFileSync(new URL('../assets/docs.js', import.meta.url), 'utf8');
const start = source.indexOf('  // --- On-this-page location and rail ');
const end = source.indexOf('  // --- Evidence-spine wash ', start);
assert.ok(start >= 0 && end > start);
const runtime = source.slice(start, end);

function harness({ count = 60, railHeight = 240, viewportHeight = 600 } = {}) {
  const frames = [], listeners = {}, observers = [], fonts = [];
  const state = { y: 0, pageHeight: 6600, headerHeight: 58, railHeight, viewportHeight,
    tocVisible: true, headingReads: 0, headerReads: 0, railReads: 0, topWrites: 0 };
  const on = (target, type, fn) => (listeners[target + ':' + type] ||= []).push(fn);
  const links = Array.from({ length: count }, (_, i) => {
    const attrs = { href: '#h' + i }, classes = new Set();
    return { attrs, classes, getAttribute: key => attrs[key],
      setAttribute(key, value) { attrs[key] = value; }, removeAttribute(key) { delete attrs[key]; },
      classList: { add: value => classes.add(value), remove: value => classes.delete(value) } };
  });
  const headings = links.map((_, i) => ({ top: 100 + 100 * i, visible: true,
    getClientRects() { state.headingReads++; return this.visible ? [{}] : []; },
    getBoundingClientRect() { state.headingReads++; return { top: this.top - state.y }; },
    closest() { return this; } }));
  const toc = { getClientRects: () => state.tocVisible ? [{}] : [],
    get offsetHeight() { state.railReads++; return state.railHeight; },
    style: { set top(value) { state.topWrites++; this.value = value; }, get top() { return this.value; } } };
  const header = { getBoundingClientRect() { state.headerReads++; return { height: state.headerHeight }; } };
  const document = { body: {}, documentElement: { get scrollHeight() { return state.pageHeight; } },
    fonts: { ready: { then(fn) { fonts.push(fn); } } },
    querySelector: selector => selector === '.docs-toc' ? toc : header,
    querySelectorAll: () => links, getElementById: id => headings[Number(id.slice(1))],
    addEventListener: (type, fn) => on('document', type, fn) };
  class ResizeObserver {
    constructor(callback) { this.callback = callback; this.targets = []; observers.push(this); }
    observe(node) { this.targets.push(node); }
  }
  const window = { get pageYOffset() { return state.y; }, get scrollY() { return state.y; },
    get innerHeight() { return state.viewportHeight; }, ResizeObserver,
    requestAnimationFrame(fn) { frames.push(fn); },
    addEventListener: (type, fn) => on('window', type, fn) };
  vm.runInNewContext(runtime, { window, document, ResizeObserver });
  function emit(target, type) { (listeners[target + ':' + type] || []).forEach(fn => fn()); }
  function flush() { const pending = frames.splice(0); pending.forEach(fn => fn()); }
  function scroll(y) { state.y = y; emit('window', 'scroll'); flush(); }
  function active() { return links.findIndex(link => link.attrs['aria-current'] === 'location'); }
  function resetCounts() { state.headingReads = state.headerReads = state.railReads = state.topWrites = 0; }
  return { state, links, headings, toc, document, observers, fonts, listeners, frames,
    emit, flush, scroll, active, resetCounts };
}

test('ordinary scrolling reads only boundary headings and never rewrites a short rail', () => {
  const h = harness();
  h.scroll(2000);
  assert.equal(h.active(), 19);
  h.resetCounts();
  for (let y = 2010; y < 2500; y += 10) h.scroll(y);
  assert.equal(h.active(), 24);
  assert.ok(h.state.headingReads <= 49 * 4, 'two boundary headings, not the whole corpus');
  assert.equal(h.state.headerReads, 0);
  assert.equal(h.state.railReads, 0);
  assert.equal(h.state.topWrites, 0);
  h.emit('window', 'scroll'); h.emit('window', 'scroll'); h.emit('window', 'scroll');
  assert.equal(h.frames.length, 1, 'multiple scroll events share one frame');
});

test('closed headings stay excluded and the bottom selects the final visible heading', () => {
  const h = harness({ count: 6 });
  h.headings[2].visible = false;
  h.headings[5].visible = false;
  h.emit('document', 'toggle'); h.flush();
  h.scroll(240);
  assert.equal(h.active(), 1);
  h.scroll(6000);
  assert.equal(h.active(), 4);
  h.headings[2].visible = true;
  h.emit('document', 'toggle'); h.flush();
  h.scroll(240);
  assert.equal(h.active(), 2);
});

test('late reflow at the reading boundary is repaired before choosing a section', () => {
  const h = harness({ count: 10 });
  h.scroll(450);
  assert.equal(h.active(), 4);
  h.headings.slice(2).forEach(heading => { heading.top += 300; });
  h.scroll(450);
  assert.equal(h.active(), 1, 'cached section four moved below the reading line');
});

test('layout, fonts, load, disclosure and content-visibility signals refresh geometry', () => {
  const signals = [
    h => h.emit('window', 'resize'), h => h.emit('window', 'load'),
    h => h.emit('document', 'toggle'), h => h.emit('document', 'contentvisibilityautostatechange'),
    h => h.fonts[0](), h => h.observers[0].callback(),
  ];
  for (const signal of signals) {
    const h = harness({ count: 6 });
    h.scroll(240);
    assert.equal(h.active(), 2);
    h.headings[3].top = 320;
    signal(h); h.flush();
    assert.equal(h.active(), 3);
    assert.ok(h.observers[0].targets.includes(h.headings[3]), 'watch section size changes');
  }
});

test('the tall rail follows native page progress and reacts to page growth', () => {
  const h = harness({ railHeight: 1000 });
  assert.equal(h.toc.style.top, '58px');
  h.scroll(3000);
  assert.equal(Number.parseFloat(h.toc.style.top), -183);
  h.scroll(6000);
  assert.equal(h.toc.style.top, '-424px');
  h.state.pageHeight = 12600;
  h.scroll(6000);
  assert.equal(Number.parseFloat(h.toc.style.top), -183, 'new page height affects progress immediately');
  assert.equal(h.active(), 59);
  assert.ok(!h.listeners['window:wheel'] && !h.listeners['window:touchmove']);
});

test('responsive hidden rails do no heading work until visible again', () => {
  const h = harness();
  h.state.tocVisible = false;
  h.emit('window', 'resize'); h.flush();
  h.resetCounts();
  h.scroll(1200); h.scroll(2200);
  assert.equal(h.state.headingReads, 0);
  h.state.tocVisible = true;
  h.emit('window', 'resize'); h.flush();
  assert.equal(h.active(), 21);
});

test('a rail hidden or shown without resize is checked before heading work', () => {
  const h = harness();
  h.state.tocVisible = false;
  h.resetCounts();
  h.scroll(1200);
  assert.equal(h.state.headingReads, 0);
  h.state.tocVisible = true;
  h.scroll(1200);
  assert.equal(h.active(), 11);
});

test('viewport changes are reconciled before page-end selection even without a resize event', () => {
  const h = harness({ count: 2 });
  h.headings[1].top = 1000;
  h.emit('document', 'toggle'); h.flush();
  h.state.pageHeight = 1500;
  h.state.viewportHeight = 900;
  h.scroll(600);
  assert.equal(h.active(), 1, 'the short final section is selected at the actual page bottom');
});

test('a rail above the scrollspy budget retains its complete native scroll range', () => {
  const h = harness({ count: 90, railHeight: 1200 });
  h.scroll(6000);
  assert.equal(h.active(), -1);
  assert.equal(h.toc.style.top, '-624px');
  assert.equal(h.state.headingReads, 0);
});
