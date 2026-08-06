import { test } from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = dirname(fileURLToPath(import.meta.url));
const SITE = join(HERE, '..');
const SOURCE = readFileSync(join(SITE, 'assets', 'docs-loader.js'), 'utf8');
const PAPERS = readFileSync(join(SITE, 'docs', 'papers.html'), 'utf8');

function action(tag, attrs = {}) {
  const node = {
    tagName: tag.toUpperCase(),
    _attrs: { ...attrs },
    clicks: 0,
    setAttribute(key, value) { this._attrs[key] = String(value); },
    getAttribute(key) { return Object.hasOwn(this._attrs, key) ? this._attrs[key] : null; },
    addEventListener() {},
    matches(selector) {
      return selector.includes('narrative-ref--term') &&
        (this._attrs.class || '').includes('narrative-ref--term') &&
        Object.hasOwn(this._attrs, 'data-term');
    },
    closest(selector) {
      if (this.tagName === 'A' && selector.includes('a[href]')) return this;
      if (this.tagName === 'BUTTON' && selector.includes('button')) return this;
      return null;
    },
    click() { this.clicks += 1; },
  };
  return node;
}

function harness() {
  const listeners = {};
  const windowListeners = {};
  const scripts = [];
  const idle = [];
  const timers = [];
  const rootAttrs = {};
  const storage = {};
  const runtimeRef = { getAttribute: (key) => key === 'src' ? '../assets/docs.js?v=runtime' : null };
  const template = { content: { querySelector: () => runtimeRef } };

  const document = {
    readyState: 'loading',
    body: { appendChild(node) { scripts.push(node); } },
    documentElement: {
      scrollTop: 0,
      setAttribute(key, value) { rootAttrs[key] = String(value); },
    },
    activeElement: null,
    title: 'The papers · Plectis docs',
    querySelector(selector) {
      if (selector === 'template[data-plectis-runtime="docs"]') return template;
      if (selector === 'main h1, h1') return { textContent: 'The papers' };
      return null;
    },
    querySelectorAll(selector) {
      if (selector === 'details[open][id]') return [];
      return [];
    },
    createElement(tag) {
      const node = action(tag);
      node._listeners = {};
      node.addEventListener = function (type, fn) { this._listeners[type] = fn; };
      return node;
    },
    addEventListener(type, fn) { (listeners[type] || (listeners[type] = [])).push(fn); },
    removeEventListener(type, fn) {
      const rows = listeners[type] || [];
      const at = rows.indexOf(fn);
      if (at >= 0) rows.splice(at, 1);
    },
  };
  const window = {
    location: {
      href: 'https://example.test/docs/papers.html',
      origin: 'https://example.test',
      pathname: '/docs/papers.html',
      search: '',
      hash: '',
    },
    pageYOffset: 0,
    requestIdleCallback(fn) { idle.push(fn); },
    setTimeout(fn) { timers.push(fn); },
    addEventListener(type, fn) { (windowListeners[type] || (windowListeners[type] = [])).push(fn); },
    sessionStorage: {
      getItem(key) { return Object.hasOwn(storage, key) ? storage[key] : null; },
      setItem(key, value) { storage[key] = String(value); },
    },
  };
  const context = { document, window, URL, MouseEvent: class {}, console };
  vm.runInNewContext(SOURCE, context, { filename: 'docs-loader.js' });
  return { listeners, windowListeners, scripts, idle, timers, rootAttrs, storage };
}

function fire(rows, type, event = {}) {
  for (const fn of (rows[type] || []).slice()) fn(event);
}

test('generated docs load only the small scheduler on the critical path', () => {
  assert.match(PAPERS, /<template data-plectis-runtime="docs"><script src="\.\.\/assets\/docs\.js\?v=/);
  assert.match(PAPERS, /<script defer src="\.\.\/assets\/docs-loader\.js\?v=/);
  assert.doesNotMatch(PAPERS, /<link rel="preload" href="\.\.\/assets\/docs\.js/);
  assert.doesNotMatch(PAPERS, /<script defer src="\.\.\/assets\/docs\.js/);
});

test('full docs runtime waits until the post-load idle slot', () => {
  const page = harness();
  assert.equal(page.rootAttrs['data-plectis-docs-runtime'], 'staged');
  assert.equal(page.scripts.length, 0);

  fire(page.windowListeners, 'load');
  assert.equal(page.scripts.length, 0, 'window load alone does not start heavyweight JS');
  assert.equal(page.idle.length, 1);
  page.idle.shift()({ didTimeout: false, timeRemaining: () => 8 });
  assert.equal(page.scripts.length, 1);
  assert.match(page.scripts[0].src, /docs\.js\?v=runtime/);
  assert.equal(page.rootAttrs['data-plectis-docs-runtime'], 'loading');

  page.scripts[0]._listeners.load();
  assert.equal(page.rootAttrs['data-plectis-docs-runtime'], 'ready');
});

test('an enhanced first click is held and replayed after runtime activation', () => {
  const page = harness();
  const button = action('button');
  const click = {
    target: button,
    button: 0,
    preventDefault() { this.prevented = true; },
    stopImmediatePropagation() { this.stopped = true; },
  };

  fire(page.listeners, 'pointerdown', { target: button });
  assert.equal(page.scripts.length, 1, 'real intent starts docs immediately');
  fire(page.listeners, 'click', click);
  assert.equal(click.prevented, true);
  assert.equal(click.stopped, true);
  assert.equal(button.clicks, 0);

  page.scripts[0]._listeners.load();
  while (page.timers.length) page.timers.shift()();
  assert.equal(button.clicks, 1, 'the original action runs once against ready handlers');
});

test('ordinary links stay native while preserving the exact-return seed', () => {
  const page = harness();
  const link = action('a', { href: 'glossary.html#glossary-system' });
  const click = {
    target: link,
    button: 0,
    preventDefault() { this.prevented = true; },
    stopImmediatePropagation() { this.stopped = true; },
  };

  fire(page.listeners, 'click', click);
  assert.equal(click.prevented, undefined, 'navigation is never held for enhancement');
  assert.equal(click.stopped, undefined);
  assert.equal(page.scripts.length, 1, 'the destination runtime still starts warming');
  const trail = JSON.parse(page.storage['mc:viewstate:stack']);
  assert.equal(trail.length, 1);
  assert.equal(trail[0].path, '/docs/papers.html');
  assert.equal(trail[0].title, 'The papers');
});
