import { test } from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = dirname(fileURLToPath(import.meta.url));
const SITE = join(HERE, '..');
const HTML = readFileSync(join(SITE, 'index.html'), 'utf8');
const GLOSSARY = readFileSync(join(SITE, 'docs', 'glossary.html'), 'utf8');
const SOURCE = readFileSync(join(SITE, 'assets', 'landing.js'), 'utf8');
const DOCS_RUNTIME = readFileSync(join(SITE, 'assets', 'docs.js'), 'utf8');
const TERM_PREVIEWS = readFileSync(join(SITE, 'assets', 'term-previews.js'), 'utf8');

function glossaryTerm(id) {
  const context = { window: {} };
  vm.runInNewContext(TERM_PREVIEWS, context, { filename: 'term-previews.js' });
  return context.window.__MICROCOSM_TERM_PREVIEWS__.terms.find((term) => term.object_id === `term:${id}`);
}

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

test('the first narrative Plectis reference offers its glossary preview exactly once', () => {
  assert.match(
    HTML,
    /<p class="hero__lede"><a class="narrative-ref narrative-ref--term" href="docs\/glossary\.html#glossary-plectis" data-term="plectis">Plectis<\/a> contains/,
  );
  assert.equal((HTML.match(/data-term="plectis"/g) || []).length, 1);
});

test('Plectis preview explains the name in this project, not only its Latin root', () => {
  const plectis = glossaryTerm('plectis');
  assert.equal(
    plectis.reader_preview,
    'Plectis is the public name for this project: the site, the reader-facing map, the components and papers it presents, and the public source repository behind them. Its name comes from the Latin plectere, to weave or entwine: it describes the public surface that gathers those separate, source-linked parts into one readable whole.',
  );
  assert.doesNotMatch(plectis.reader_preview, /[—*]/);
  assert.match(GLOSSARY, /In context, it names the readable public surface/);
  assert.match(HTML, /assets\/docs\.js\?v=plectis-context-v2/);
  assert.match(DOCS_RUNTIME, /term-previews\.js\?v=plectis-context-v2/);
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
