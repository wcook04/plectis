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
    documentElement: { scrollTop: 0, setAttribute(key, value) { roots[key] = value; } },
    activeElement: null,
    title: 'Plectis',
    querySelectorAll(selector) {
      if (selector === 'template[data-plectis-runtime]') return refs;
      if (selector === 'details[open][id]') return [];
      return [];
    },
    querySelector() { return null; },
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

test('landing keeps heavyweight runtimes inert behind the small scheduler', () => {
  assert.match(HTML, /<template data-plectis-runtime="docs"><script src="assets\/docs\.js\?v=/);
  assert.match(HTML, /<template data-plectis-runtime="art"><script src="assets\/art\.js\?v=/);
  assert.match(HTML, /<script async src="assets\/landing\.js\?v=/);
  assert.doesNotMatch(HTML, /<script async src="assets\/(?:docs|art)\.js/);
  assert.match(SOURCE, /var eased = 1 - Math\.pow\(1 - p, 3\)/);
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
